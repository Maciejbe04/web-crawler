import requests,re, urllib.parse as urp, threading, time
from concurrent.futures import ThreadPoolExecutor, wait
import sys, getopt,os
from rich import print
import signal
import queue

class Spider:

    valid_codes = [200,201,204,301,302,405,500]

    blacklist = ['cloudflare', 'google']

    scope_regex = r"(?:https?:\/\/.*)\.([\w]+\.[\w]+)\/"

    scope = ""

    extensions = ['.js', '.html', ".php", '.css', '.ico', "txt"]

    visited = set()
    found = set()
    static_page_pattern = r"(https?:\/\/[\w][\w\W]+?[\"\'\>\<\s])"
    referer_pattern = r"href=\"(.+?)[\"\'\>\<\s]"

    def __init__(self, url:str, depth:int, threads:int):
        self.url = url
        self.depth = depth
        self.validate_fields()
        Spider.scope = re.search(Spider.scope_regex, self.url).group(1)
        self.lock = threading.Lock()
        self.threads = threads
        self.queue = queue.Queue()
        self.depth_dict = {}
        self.current_depth = 0



    def grab_links(self, url):

        content = ""
        
        response_url = self.parse_url(url)

        print(f"{response_url} parsed" )

        with self.lock:
            if response_url in Spider.visited:
                return [], None
            Spider.visited.add(response_url)
    
        try:
            
            response = requests.get(response_url)
            response_url = response.url
            content = response.text

            print(f"{response_url} response" )

            if response.status_code not in Spider.valid_codes:
                Spider.visited.remove(response_url)
                return [], None
                
        except requests.exceptions.ConnectionError as ex:
            print("couldnt connect")
            return [], None

        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        return all_links, response_url

    def bfs(self, url):

        links, response_url = self.grab_links(url)

        if response_url == None:
            self.queue.task_done()
            return 

        for link in links:

            normalized_path = self.normalize_path(response_url, link)
            
            if "https://" in link or "http://" in link:
                normalized_path = link

            with self.lock:
                if normalized_path in Spider.found:
                    continue
                self.depth_dict[normalized_path] = self.current_depth
                Spider.found.add(normalized_path)

            if self.current_depth == self.depth:
                with self.lock:
                    Spider.found.add(normalized_path)
                continue

            self.queue.put(normalized_path)

        self.queue.task_done()
                     
    def queue_handler(self):

        self.queue.put(self.url)
        self.depth_dict[self.url] = 0


        with ThreadPoolExecutor(max_workers=self.threads) as exe:

            while True:
                self.current_depth += 1
                if self.current_depth > self.depth:
                    break

                while True:
                    futures = []
                    for _ in range(self.threads):
                        try:
                            link = self.queue.get(block=False)
                        except queue.Empty:
                            break

                        future = exe.submit(self.bfs, link)

                        futures.append(future)
                        
                    if len(futures) == 0:
                        return False

                    if self.current_depth != self.depth:
                        wait(futures)
            
   
    

    def initialize(self):

        print(f"[*] Crawling... [bold red]{self.url}[/bold red]")
        print(f"[*] Options THREADS = [bold green]{self.threads}[/bold green], DEPTH = [bold bright_magenta]{self.depth}[/bold bright_magenta]")

        self.queue_handler()

    def format_results(self):

        print(f"[+] Found links for [bold red]{self.url}[/bold red] website")
        print("=======================================")

        for link in Spider.found:
            print(f"[+] [bold green]{link}[/bold green]")
        print("=======================================")
        print(f"[+] Found [bold blink medium_spring_green]{len(Spider.found)} [/bold blink medium_spring_green]links")
        print("=======================================")
        print(self.depth_dict)
        print(len(self.depth_dict))
        print(f"Working links {len(Spider.visited)}")


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
    spider.initialize()
    stop_time = time.time()
    spider.format_results()

    print(f"Execution finished in {stop_time - start_time} seconds")
    
if __name__ == "__main__":
    os.environ.pop("NO_COLOR", None)
    main()
 