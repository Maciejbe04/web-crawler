import requests,re, urllib.parse as urp, threading, time
from concurrent.futures import ThreadPoolExecutor, wait
import sys, getopt,os
from rich import print
import signal


class Spider:

    valid_codes = [200,201,204,301,302,405,500]

    blacklist = ['cloudflare', 'google']

    scope_regex = r"(?:https?:\/\/.*)\.([\w]+\.[\w]+)\/"

    scope = ""

    extensions = ['.js', '.html', ".php", '.css', '.ico', "txt"]

    depth_dict = {}

    visited = set()
    static_page_pattern = r"(https?:\/\/[\w][\w\W]+?[\"\'\>\<\s])"
    referer_pattern = r"href=\"(.+?)[\"\'\>\<\s]"
    current_depth = 0

    def __init__(self, url:str, depth:int, threads:int):
        self.url = url
        self.depth = depth
        self.validate_fields()
        Spider.scope = re.search(Spider.scope_regex, self.url).group(1)
        self.lock = threading.Lock()
        self.threads = threads
        self.tasks = []
        Spider.executor = None

    def init_crawl(self, url):

        content = ""

        response_url = self.parse_url(url)

        if response_url in Spider.visited:
            return    
        
        try:
            content = requests.get(self.url.strip()).text
            Spider.visited.add(self.url)
            response_url = self.url

        except requests.exceptions.ConnectionError as ex:
            print("couldnt connect")
            return 

        Spider.visited.add(response_url)

        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        with ThreadPoolExecutor(max_workers=self.threads) as ex:

            self.executor = ex

            for link in all_links:

                normalized_path = self.normalize_path(response_url, link)
                
                if "https://" in link or "http://" in link:
                    normalized_path = link
                
                if normalized_path in Spider.visited:
                    continue

                future = ex.submit(self.crawl, normalized_path, 0, ex)
                self.tasks.append(future)

            while True:
                with self.lock:
                    pending = [f for f in self.tasks if not f.done()]
                    if not pending:
                        break
                wait(pending)
                
                                   
            
  

    def crawl(self,url, depth,executor):

        if depth > self.depth:
            return 

        content = ""

        response_url = self.parse_url(url)

        with self.lock:
            if response_url in Spider.visited:
                return 
            Spider.visited.add(response_url)

        print(depth)
        
        try:
            response = requests.get(response_url, timeout=5)

            content = response.text

            response_url = response.url
                
            if response.status_code not in Spider.valid_codes:
                return 

        except requests.exceptions.ConnectionError as ex:
            print(f"Couldnt connect to adress {response_url}")
            return 


        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        for link in all_links:

            normalized_path = self.normalize_path(response_url, link)

            if "https://" in link or "http://" in link:
                normalized_path = link

            if normalized_path not in Spider.visited:
                f = executor.submit(self.crawl, normalized_path, depth+1, executor)
                with self.lock:
                    self.tasks.append(f)
            else:
                continue

    def initialize(self):

        print(f"[*] Crawling... [bold red]{self.url}[/bold red]")
        print(f"[*] Options THREADS = [bold green]{self.threads}[/bold green], DEPTH = [bold bright_magenta]{self.depth}[/bold bright_magenta]")

        self.init_crawl(self.url)

    def format_results(self):

        print(f"[+] Found links for [bold red]{self.url}[/bold red] website")
        print("=======================================")

        for link in self.visited:
            print(f"[+] [bold green]{link}[/bold green]")
        print("=======================================")
        print(f"[+] Found [bold blink medium_spring_green]{len(self.visited)} [/bold blink medium_spring_green]links")
        print("=======================================")


    def validate_fields(self):

        if self.depth < 0:
            raise Exception("invalid depth")

    def filter_scope(self, origin_list:list) -> list:

        filtered_list = []

        for origin in origin_list:
            if self.scope in origin:
                filtered_list.append(origin)

        return filtered_list

    def parse_url(self, url:str) -> str:

        parsed = ""

        if any(substring in url for substring in Spider.extensions):
            return url
        
        if url[-1] != "/":
            parsed = url+"/"
            return parsed
        
        return url

    def normalize_path(self, path:str,second_path:str) -> str:

        normalized = urp.urljoin(path, second_path)

        return normalized

def usage():
    print("-u --url=str specify target url")
    print("-d --depth=int specify crawling depth. Default value 1 ")
    print("-t --threads=int specify thread count. Default value 10")
    print("-h --help view help")


def handle_signal(signum,frame):

    if Spider.executor is not None:
        Spider.executor.shutdown(wait=True, cancel_futures=True)
        with open('output.txt', 'w') as file:
            for link in Spider.visited:
                file.write(link + "\n")

    sys.exit(2)


def main():


    
    url = ""
    depth = 1
    threads = 10
    
    if len(sys.argv) < 2:
        usage()
        sys.exit(2)
    
    opt, args = None, None
    
    try:
        opt, args = getopt.getopt(sys.argv[1:], "u:d:t:h", ["url=","depth=", "threads=", "help"])
    except getopt.error as error:
        print(error.msg)
        usage()
        sys.exit(2)

    for o, a in opt:
        if o in ("-u", "--url"):
            url = a
        elif o in("-d", "--depth"):
            depth = int(a)
        elif o in ("-t", "--threads"):
            threads = int(a)
        elif o in ("-h", "--help"):
            usage()
            exit(0)
        else:
            usage()
            exit(2)

    spider = Spider(url=url, depth=depth, threads=threads)

    start_time = time.time()
    signal.signal(signal.SIGINT, handle_signal)
    spider.initialize()
    stop_time = time.time()
    spider.format_results()

    print(f"Execution finished in {stop_time - start_time} seconds")
    
if __name__ == "__main__":
    os.environ.pop("NO_COLOR", None)
    main()
