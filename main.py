import requests,re, urllib.parse as urp, threading
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
            Spider.depth_dict[response_url] = 0

        except requests.exceptions.ConnectionError as ex:
            print("couldnt connect")
            return 0

        Spider.visited.add(response_url)

        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        threads = []

        for link in all_links:

            normalized_path = self.normalize_path(response_url, link)

            thread_depth = 0
            
            if "https://" in link and "http://" in link:
                normalized_path = link
            
            if normalized_path not in Spider.visited:
                thread_depth = 0
            else:
                continue

            t = threading.Thread(target=self.crawl, args=(normalized_path,thread_depth))


            
        print(all_links)
        for t in threads:
            t.start()

        for t in threads:
            t.join()
            
    def create_thread_pool(self):

        pass
        

    def crawl(self,url, depth):

        if depth > self.depth:
            return 0

        content = ""

        response_url = self.parse_url(url)

        with self.lock:
            if response_url in Spider.visited:
                return 0
        
        try:
            response = requests.get(response_url, timeout=5)

            content = response.text

            response_url = response.url
                
            if response.status_code not in Spider.valid_codes:
                return 0

            Spider.depth_dict[response_url] = 0

        except requests.exceptions.ConnectionError as ex:
            print("Couldnt connect to adress")
            return 0

        with self.lock:
            Spider.visited.add(response_url)

        list_of_static_links = re.findall(Spider.static_page_pattern, content)
        list_of_referals = re.findall(Spider.referer_pattern, content)

        all_links = self.filter_scope(list_of_static_links) + list_of_referals

        for link in all_links:

            normalized_path = self.normalize_path(response_url, link)

            if "https://" in link and "http://" in link:
                normalized_path = link

            if normalized_path not in Spider.visited:
                self.crawl(normalized_path, depth+1)
            else:
                continue

    def initialize(self):

        self.init_crawl(self.url)

    def format_results(self):


        print(f"Exec options: DEPTH: {self.depth} ")
        print(f"[+] Found links for {self.url} website")
        print("=======================================")

        for link in self.visited:
            print(link + "\n")

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

    
if __name__ == "__main__":
    spider = Spider(url="https://books.toscrape.com/", depth=2, threads=10)
    spider.initialize()
    spider.format_results()
