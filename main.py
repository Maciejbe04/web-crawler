import requests,re, urllib.parse as urp, threading, time
from concurrent.futures import ThreadPoolExecutor

class Spider:

    valid_codes = [200,201,301,302,405]

    blacklist = ['cloudflare', 'google']

    scope_regex = r"(?:https?:\/\/.*)\.([\w]+\.[\w]+)\/"

    scope = ""

    extensions = ['.js', '.html', ".php", '.css', '.ico']

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

    def init_crawl(self, url):

        content = ""

        response_url = self.parse_url(url)

        if response_url in Spider.visited:
            return 0    
        
        try:
            content = requests.get(self.url.strip()).text
            Spider.visited.add(self.url)
            response_url = self.url

        except requests.exceptions.ConnectionError as ex:
            print("couldnt connect")
            return 0

        Spider.visited.add(response_url)

        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        with ThreadPoolExecutor(max_workers=self.threads) as ex:
            for link in all_links:

                normalized_path = self.normalize_path(response_url, link)

                thread_depth = 0
                
                if "https://" in link and "http://" in link:
                    normalized_path = link
                
                if normalized_path not in Spider.visited:
                    thread_depth = 0
                else:
                    continue

                ex.submit(self.crawl, normalized_path, 0, ex)
            
  

    def crawl(self,url, depth,executor):

        if depth > self.depth:
            return 

        content = ""

        response_url = self.parse_url(url)

        with self.lock:
            if response_url in Spider.visited:
                return 
            Spider.visited.add(response_url)
        
        try:
            response = requests.get(response_url, timeout=5)

            content = response.text

            response_url = response.url
                
            if response.status_code not in Spider.valid_codes:
                return 0

        except requests.exceptions.ConnectionError as ex:
            print("Couldnt connect to adress")
            return 0


        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        for link in all_links:

            normalized_path = self.normalize_path(response_url, link)

            if "https://" in link or "http://" in link:
                normalized_path = link

            if normalized_path not in Spider.visited:
                executor.submit(self.crawl, normalized_path, depth+1, executor)
            else:
                continue

    def initialize(self):

        print(f"[*] Crawling... {self.url}")

        self.init_crawl(self.url)

    def format_results(self):


        print(f"Exec options: DEPTH: {self.depth} ")
        print(f"[+] Found links for {self.url} website")
        print("=======================================")

        for link in self.visited:
            print(link)
        print("=======================================")
        print(f"[+] Found {len(self.visited)} links")
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


def main():
    spider = Spider(url="https://books.toscrape.com/", depth=1, threads=15)

    start_time = time.time()
    spider.initialize()
    spider.format_results()

    print(f"Execution finished in {time.time() - start_time} seconds")
    
if __name__ == "__main__":

    main()
