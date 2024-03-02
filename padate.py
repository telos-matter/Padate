#! /usr/bin/env python

import requests
import argparse
import os
from html.parser import HTMLParser
from urllib.parse import urlparse
from enum import Enum, auto

# Define the arg parser
arg_parser = argparse.ArgumentParser(
    prog='Padate',
    description='''Checks a website continuously for updates and notifies the user when one occurs.''',
    epilog='https://github.com/telos-matter/Padate'
    )

def check_positive_int (value: str) -> int:
    '''Used in arg_parser only'''
    try:
        value = int(value)
        if value >= 0:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f'{value} must be a positive integer value.')

# Add the arg parser arguments
arg_parser.add_argument('url', type=str, help='the url of the website to watch / check.')
arg_parser.add_argument('-p' , '--period', type=check_positive_int, help='the period, in seconds, to wait after each check. The default is 0 seconds.', default=0)
arg_parser.add_argument('-q', '--quiet', action='store_true', help="signal only important stuff to the user")
arg_parser.add_argument('-c', '--crash', action='store_true', help='halt the process if a website is unreachable or unable to be parsed when watching.')
arg_parser.add_argument('-d', '--depth', type=check_positive_int, help='how far deep should the links be followed and checked. 0 means only check the supplied url, 1 means check the supplied url and all of the links / urls that its page has, and so on. Be cautious as that even a value of 2 could lead to a very large tree of pages. The default is 0.', default=0)
arg_parser.add_argument('-i', '--ignore', type=str, nargs='+', help='websites to be ignored in the sub-links. Default websites are: www.facebook.com, www.google.com, www.twitter.com, www.x.com, www.youtube.com, and www.reddit.com',
                        default=['www.facebook.com',
                                'www.google.com',
                                'www.twitter.com',
                                'www.x.com',
                                'www.youtube.com',
                                'www.reddit.com'])

# Parse the args
ARGS = arg_parser.parse_args()

class Page (HTMLParser):
    '''Describes a web page
    Uses HTMLParser to parse it self'''
    
    class __HTMLSection (Enum):
        '''Defines the HTML sections'''
        HEAD = auto()
        BODY = auto()
    
    # The tags that are usually used inside the <body> and that are not visible
    __INVISIBLE_BODY_TAGS = [
        'script',
        'style',
        'meta',
        'link',
        'template',
        'iframe',
    ]
    
    # A set that contains all the urls that are checked. As to not form a loop
    __urls = set()
    
    @classmethod
    def prep_url (cls, url: str) -> str:
        '''Prepares a url by adding the needed http://'''
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' +url
        return url
    
    def __init__(self, url: str, level: int, first_iteration: bool, *, struct_tol: int=2) -> None:
        '''
        - `url`: the url of this page
        - `level`: the level of this page, 0 would be the main page,
        - `first_iteration`: whether or not this is the first time pinging the pages
        1 would be pages inside of it, and so on..
        - `struct_tol`: How wrong can the HTML structure be and still tolerate it?
            - 0: no tolerance
            - 1: minor tolerance (paragraphs don't need to close for example)
            - 2: just parse it dude
        '''
        super().__init__(convert_charrefs=True)
        
        assert url not in Page.__urls, f"This url `{url}` has been added twice!"
        Page.__urls.add(url)
        
        self.url              = url # The url of this page
        self.netloc           = urlparse(url).netloc # The network location of the url
        self.valid_response   = False # Have we gotten a valid response from this page?
        self.status  = 'Yet to make request.' # A message indicating the current status
        self.problems_counter = 0 # How many problems have been encountered when parsing, regardless of tolerance level
        self.level            = level # How far deep is this page?
        self.title            = None # The pages' title
        self.content          = [] # The pages' content in the order it is encountered in
        self.sub_pages        = [] # Pages inside the page
        
        self.__first_iteration = first_iteration # Whether or not this is the first iteration
        self.__struct_tol      = struct_tol # How tolerant are we with the structure of the page?
        self.__section_count   = 0 # How many sections have we seen so far?
        self.__current_section = None # Which section are we currently parsing?
        self.__current_tag     = None # Which tag are we currently parsing?
        self.__tag_stack       = [] # A stack to handle nested tags
        
        try:
            # Try and make a request to the url
            if first_iteration:
                print(f"[{self.level}] Pinging: `{self.url}`")
            response = requests.get(self.url)
            
            # See if response can be read
            if response.status_code == 200 and response.headers['Content-type'].startswith('text/html'):
                # If it can, start parsing
                self.feed(response.text)
                # If all went well then the response was valid
                self.valid_response = True
                # Update status accordingly
                if self.problems_counter == 0:
                    self.status = 'All OK.'
                else:
                    self.status = 'OK.'
            # If it cannot be read then just update the status
            else:
                if response.status_code != 200:
                    self.status = f'Page responded with code {response.status_code}'
                else:
                    self.status = f"Page's content-type is {response.headers['Content-type']}"
        
        except AssertionError as assertion:
            raise assertion
        except Exception as e:
            self.status = f"Couldn't parse the page because this error: {e}"
        
        # If a sub_page on the first iteration failed, then stop
        if self.level != 0 and self.__first_iteration and not self.valid_response:
            raise Exception(f"Halted process because this page was unreachable: {self.url}")
    
    def anything_wrong (self) -> 'Page | None':
        '''Returns the first Page that
        couldn't have been parsed in this tree of pages'''
        
        if not self.valid_response:
            return self
        for page in self.sub_pages:
            page = page.anything_wrong()
            if page is not None:
                return page
        return None
    
    def all_good (self) -> bool:
        '''Returns whether or not this page and its sub_pages
        have all been parsed successfully'''
        
        return self.anything_wrong() is None
    
    def pages_count (self) -> int:
        '''Returns how many pages are there in this tree'''
        
        count = 1 # Self
        for page in self.sub_pages:
            count += page.pages_count()
        return count
    
    def tree_as_str (self) -> str:
        '''Visualize this tree'''
        
        tree = '->' if self.level == 0 else (os.linesep + (self.level * '  ') + '└>')
        tree += ' ' +self.url
        for page in self.sub_pages:
            tree += page.tree_as_str()
        return tree
    
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        '''Handle starting tags like `<p>`'''
        
        def is_ignored (url: str) -> bool:
            '''Is this url one of the ignored ones?'''
            netloc = urlparse(url).netloc
            return netloc in ARGS.ignore
        
        # Update current_tag
        self.__current_tag = tag
        # Push into the stack
        self.__tag_stack.append(tag)
        
        # Check if the conditions are met to check a sub page
        if (self.__current_section is Page.__HTMLSection.BODY and # If we are in the BODY, and
                tag == 'a' and # It's an anchor tag, and
                self.level < ARGS.depth): # We haven't reached max depth yet
            # Then look for the href attribute, and retrieve its value
            for key, value in attrs:
                if key == 'href':
                    # Once we found the href attribute, first see if it's useful
                    if value is None or value.isspace() or value in ['/', '#'] or value.startswith('#'):
                        break
                    # If not, see if it's self reference, if so update it accordingly
                    if value.startswith('/'):
                        value = self.netloc + value
                    # Prepare the url
                    value = Page.prep_url(value)
                    # Finally, see if it's eligible to be added
                    if not is_ignored(value) and value not in Page.__urls:
                        self.sub_pages.append(Page(value, self.level +1, self.__first_iteration))
                    # If it's not eligible to be added, then just break out of the loop
                    else:
                        break
        
        # Check if the tag defines a section
        # Case it's <head>
        if tag == 'head':
            # Inc the count
            self.__section_count += 1
            # If the current_section is not None or if the section_count is not 1, then the page is invalid
            if self.__current_section is not None or self.__section_count != 1:
                self.problems_counter += 1
                if self.__struct_tol <= 1:
                    line, col = self.getpos()
                    raise Exception(f"Was not expecting to encounter <head> here; line: {line}, col: {col}.")
            # Otherwise the current section is HEAD
            self.__current_section = Page.__HTMLSection.HEAD
            
        # Case it's <body>
        elif tag == 'body':
            # Inc the count
            self.__section_count += 1
            # If the current_section is not None or if the section_count is not 2, then the page is invalid
            if self.__current_section is not None or self.__section_count != 2:
                self.problems_counter += 1
                if self.__struct_tol <= 1:
                    line, col = self.getpos()
                    raise Exception(f"Was not expecting to encounter <body> here; line: {line}, col: {col}.")
            # Otherwise the current section is now BODY
            self.__current_section = Page.__HTMLSection.BODY
    
    def handle_endtag(self, tag):
        '''Handles closing the tags like </p>, and keeps the
        current_tag up to date using the tag_stack. Updates
        current_section too.'''
        assert tag is not None, "It can't be None, can it?"
        
        def update_current_tag(self: Page, tag: str):
            '''Updates the current_tag using the stack.
            Called after closing a tag and updating the tag_stack'''
            # Update current_tag
            if len(self.__tag_stack) != 0:
                self.__current_tag = self.__tag_stack[-1]
            else:
                self.__current_tag = None
            # If it was a section tag, update current_section
            if tag in ['head', 'body']:
                assert (tag == 'head' and self.__current_section is Page.__HTMLSection.HEAD) or (tag == 'body' and self.__current_section is Page.__HTMLSection.BODY), f"Normally, unreachable."
                self.__current_section = None
        
        # If we are closing the current_tag
        if self.__current_tag == tag:
            assert len(self.__tag_stack) >= 1 and self.__tag_stack[-1] == tag, f"Last element should be current_tag"
            # Remove current_tag from the stack, which is the last one
            self.__tag_stack.pop()
            update_current_tag(self, tag)
        # Otherwise, if we are closing something else
        else:
            self.problems_counter += 1
            # Then it's only a problem if struct_tol == 0
            if self.__struct_tol == 0:
                line, col = self.getpos()
                raise Exception(f"Closing a currently unopened tag <{tag}> at line: {line}, col: {col}.")
            # Otherwise
            else:
                # If it exists, close latest
                if tag in self.__tag_stack:
                    # Get rindex of tag
                    rindex = len(self.__tag_stack)
                    for stack_tag in self.__tag_stack[::-1]:
                        rindex -= 1
                        if stack_tag == tag:
                            break
                    # Remove everything from rindex to end
                    self.__tag_stack[rindex :] = []
                    update_current_tag(self, tag)
                # Otherwise just ignore it
                else:
                    pass
    
    def handle_data(self, data: str):
        '''Handles data inside tags like <p>this for example</p>'''
        
        # Check which section is currently being parsed
        # Case it's HEAD
        if self.__current_section is Page.__HTMLSection.HEAD:
            # Inside the HEAD, we are only interested with the title
            if self.__current_tag == 'title':
                self.title = data
        # Case it's BODY
        elif self.__current_section is Page.__HTMLSection.BODY:
            # If the current_tag is not invisible, then it's content
            if self.__current_tag not in Page.__INVISIBLE_BODY_TAGS and not data.isspace():
                self.content.append(data)

# def say(msg: str) -> None:
#     '''Prints if not quite'''
#     if not ARGS.quiet:
#         print(msg)
# TODO remove ^^^

# Try to make first connection
print(f"🛜 Pinging {ARGS.url}.. (MAX DEPTH = {ARGS.depth})")
ORIGINAL = Page(Page.prep_url(ARGS.url), 0, True)

if ORIGINAL.all_good():
    pages_count = ORIGINAL.pages_count()
    print(f"✅ Successfully retrieved {pages_count} page{'s'[:pages_count^1]}")
    print(ORIGINAL.tree_as_str())

else:
    page = ORIGINAL.anything_wrong()
    assert page is not None, f"Page can't be None because something is wrong."
    print(f"❌ Couldn't retrieve this page {page.url} (REASON: {page.status})..")




#       def getContent (url: str) -> str:
#             if not url.startswith('http://') and not url.startswith('https://'):
#                   url = 'http://' +url

#             try:
#                   headers = {"Accept-Language": "en"}
#                   response = requests.get(url, headers= headers)

#                   if response.status_code != 200:
#                         return None

#                   if not response.headers['Content-Type'].startswith('text/html'):
#                         return None

#                   return cleanContent(response.text)

#             except requests.exceptions.RequestException:
#                   return None

#       def isIgnored (url: str) -> bool:
#             for ignored in args.ignore:
#                   if url.find(ignored) != -1:
#                         return True
#             return False

#       def addAnchorsContent (content: str, contents: dict) -> bool:
#             urls = regex.findall(r'(?<=<\s*?a[.\s]*?href\s*?=\s*?").*?(?=")', content)
#             if not urls:
#                   return False

#             added = False
#             for url in urls:
#                   if url not in contents.keys() and not isIgnored(url):
#                         anchor_content = getContent(url)
#                         if anchor_content:
#                               contents [url] = anchor_content
#                               added = True
#             return added


#      


# # -------------------------------------------------------------------


#       print('Pinging', args.url, '...')

#       main_content = getContent(args.url)
#       if not main_content:
#             sys.exit(f'Unable to reach/read {args.url}')
#       contents = {args.url: main_content}

#       for _ in range (args.level): # TODO: a better solution, also a one that allows infinite depth
#             for content in contents.copy().values():
#                   addAnchorsContent(content, contents)


#       PING_DELAY = args.delay

#       print(f'Checking {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]} {["continuously", "every second", "every " +str(PING_DELAY) +" seconds"][(PING_DELAY != 0) + ((PING_DELAY != 0) * (PING_DELAY != 1))]}:')
#       for url in contents.keys():
#             print('\t->', url)

#       while True:
#             if not args.quiet:
#                   print('\nChecking...')
            
#             total_difference = 0
#             for url, content in contents.items():

#                   new_content = getContent(url)
#                   if new_content:
#                         difference = compareContent(content, new_content)
#                         total_difference = total_difference +difference

#                         if not args.quiet:
#                               print('\t',url,'->', str(difference *100) +'%', 'difference.')
#                   else:
#                         if args.crash:
#                               print('\n\n',url,'-> failed to reach/read.')
#                               print(f'\nTerminated at {datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}')
#                               sys.exit(0)
#                         elif not args.quiet:
#                               print('\t',url,'-> failed to reach/read.')

#             total_difference /= len(contents)
#             total_difference *= 100
#             if not args.quiet:
#                   print('\n\t->',str(total_difference) +'%', 'total difference.')
            
#             if total_difference > args.threshold:
#                   print('\a')
#                   print(f'\nA total change of {total_difference}% occurred at {datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")} in {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]}:')
#                   for url in contents.keys():
#                         print('\t->', url)
#                   print('Terminating')

#                   sys.exit(0)

#             time.sleep(PING_DELAY)



