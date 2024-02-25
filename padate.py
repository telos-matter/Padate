#! /usr/bin/env python

import requests
import argparse
from html.parser import HTMLParser
from enum import Enum, auto

arg_parser = argparse.ArgumentParser(
    prog='Padate',
    description='''Checks a website continuously for updates and notifies the user when one occurs.''',
    epilog='https://github.com/telos-matter/Padate'
    )

def check_positive_int (value: str) -> int:
    try:
        if int(value) >= 0:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f'{value} must be a positive integer value.')

arg_parser.add_argument('url', type=str, help='the url of the website to watch / check.')
arg_parser.add_argument('-p' , '--period', type=check_positive_int, help='the period, in seconds, to wait after each check. The default is 0 seconds.', default=0)
arg_parser.add_argument('-q', '--quiet', action='store_true', help='notify the user only about and when a change occurs.')
arg_parser.add_argument('-c', '--crash', action='store_true', help='halt the process if a website is unreachable or unable to be parsed.')
arg_parser.add_argument('-d', '--depth', type=check_positive_int, help='how far deep should the links be followed and checked. 0 means only check the supplied url, 1 means check the supplied url and all of the links / urls that its page has, and so on. The default is 0.', default=0)
arg_parser.add_argument('-i', '--ignore', type=str, nargs='+', help='websites to be ignored in the sub-links. Default websites are: facebook, google, twitter, x, youtube, and reddit', default= ['facebook', 'google', 'twitter', 'x', 'youtube', 'reddit'])

# args = arg_parser.parse_args()

URL = 'https://www.simpleweb.org/'

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
    
    def __init__(self, url: str, struct_tol: int=2) -> None:
        '''
        - `url`: the url of this page
        - `struct_tol`: How wrong can the HTML structure be and still tolerate it?
            - 0: no tolerance
            - 1: minor tolerance (paragraphs don't need to close for example)
            - 2: just parse it dude
        '''
        super().__init__(convert_charrefs=True)
        
        self.url              = url   # The url of this page
        self.valid_response   = (False, 'Not yet parsed.') # Have we gotten a valid response from this page? (Yes or No, Reason/Message)
        self.problems_counter = 0 # How many problems have been encountered when parsing, regardless of tolerance level
        self.title            = None # The pages' title
        self.content          = [] # The pages' content in the order it is encountered in
        
        self.__struct_tol      = struct_tol # How tolerant are we with the structure of the page?
        self.__section_count   = 0 # How many sections have we seen so far?
        self.__current_section = None # Which section are we currently parsing?
        self.__current_tag     = None # Which tag are we currently parsing?
        self.__tag_stack       = [] # A stack to handle nested tags
        
        # Make a request to the url
        response = requests.get(self.url)
        # See if response is "valid"
        if response.status_code == 200 and response.headers['Content-type'] == 'text/html; charset=UTF-8':
            # If it is, start parsing
            try:
                self.feed(response.text)
            except AssertionError as assertion:
                raise assertion
            except Exception as e:
                # If an exception occurred, just update the valid_response message and exit
                self.valid_response = (False, str(e))
                return
            # If all went well then the response was valid
            msg = 'All OK.' if self.problems_counter == 0 else 'OK.'
            self.valid_response = (True, msg)
    
    def handle_starttag(self, tag: str, _):
        '''Handle starting tags like `<p>`'''
        # Update current_tag
        self.__current_tag = tag
        # Push into the stack
        self.__tag_stack.append(tag)
        
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
        
        def updateCurrent_tag(self: Page, tag: str):
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
            updateCurrent_tag(self, tag)
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
                    updateCurrent_tag(self, tag)
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

page = Page(URL)
print(page.valid_response)
print(page.problems_counter)
print(page.title)
print(page.content)
# parser.feed(response.text)



# def main ():
#       import sys, argparse, re, time, datetime

#       def assertPositiveInt (value: str) -> int:
#             try:
#                   value = int(value)
#             except ValueError:
#                   raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
#             if value < 0:
#                   raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
#             return value

#       parser = argparse.ArgumentParser(description='''Checks a website continuously for updates and notifies the user when one occurs.''')
#       parser.add_argument('url', type= str, help= 'the url of the website to check')
#       parser.add_argument('-l', '--level', type= assertPositiveInt, help= 'checking level; 0 means only checking the supplied url, 1 means checking the supplied websites\' url and all of the urls that it has (such as links) and so on. The default is 0', default= 0)
#       parser.add_argument('-t', '--threshold', type= assertPositiveInt, help= 'the threshold of change upon which the user is notified. It "can range" from 0 to infinity. The default is 0 (percent), where the user is notified if any change occurs', default= 0)
#       parser.add_argument('-d' , '--delay', type= assertPositiveInt, help= 'the delay, in seconds, after every check. The default is 5 seconds', default= 5)
#       parser.add_argument('-q', '--quiet', action= 'store_true', help= 'notify the user only about/when a change occurs')
#       parser.add_argument('-c', '--crash', action= 'store_true', help= 'terminates the script if a website is unreachable or crashes')
#       parser.add_argument('-i', '--ignore', type= str, nargs= '+', help= 'websites to ignore by default. Default includes: facebook, google, twitter and youtube', default= ['facebook', 'google', 'twitter', 'youtube'])

#       args = parser.parse_args()


#       try:
#             import requests
#       except ImportError:
#             sys.exit('The requests package is missing.. Please consult the README file')
#       try:
#             import regex
#       except ImportError:
#             sys.exit('The regex package is missing.. Please consult the README file')


#       def cleanContent (content: str) -> str:
#             match = re.search(r'<\s*?body(.|\s)*?>(.|\s)*?<\s*?\/\s*?body\s*?>', content) # <body> ... </body>
#             if not match:
#                   return None

#             content = match.group()

#             for tag in ["class", "style", "id"]: # class=" ... "
#                   regex = re.compile(tag +'\s*?=\s*?"(.|\s)*?"')
#                   content = regex.sub('', content)

#             for tag in ["link", "meta"]: # <link ... >
#                   regex = re.compile('<\s*?' +tag +'(.|\s)*?>')
#                   content = regex.sub('', content)

#             for tag in ["link", "meta"]: # <link ... />
#                   regex = re.compile('<\s*?' +tag +'(.|\s)*?\/\s*?>')
#                   content = regex.sub('', content)

#             for tag in ["script", "style", "link"]: # <script> ... </script>
#                   regex = re.compile('<\s*?' +tag +'\s*?(.|\s)*?>(.|\s)*?<\s*?\/\s*?' +tag +'\s*?>')
#                   content = regex.sub('', content)

#             content = re.sub(r'data\s*?\-(.|\s)*?=\s*?"(.|\s)*?"', '', content) # data-... ...= "..."

#             content = re.sub(r'<\s*?input.*?type\s*?=\s*?"hidden".*?>', '', content, flags= re.S) # <input ... type= "hidden">

#             return content

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


#       def compareWord (old_word: str, new_word: str) -> str:
#             difference = 0
#             for old_char, new_char in zip(old_word, new_word):
#                   if old_char != new_char:
#                         difference = difference +1
            
#             if len(old_word) < len(new_word):
#                   difference = difference +len(new_word) -len(old_word)
#                   return difference / len(old_word)
#             else:
#                   difference = difference +len(old_word) -len(new_word)
#                   return difference / len(new_word)

#       def compareLine (old_line: str, new_line: str) -> float: # TODO: fix/proper solution to whitespace
#             old_line = old_line.split()
#             new_line = new_line.split()

#             if len(old_line) == 0 and len(new_line) == 0:
#                   return 0

#             difference = 0
#             for old_word, new_word in zip (old_line, new_line):
#                   difference = difference +compareWord(old_word, new_word)
            
#             if len(old_line) < len(new_line):
#                   for word in new_line[-len(new_line) +len(old_line):]:
#                         difference = difference +len(word)
#                   return difference / len(old_line)
#             else:
#                   for word in old_line[-len(old_line) +len(new_line):]:
#                         difference = difference +len(word)
#                   return difference / len(new_line)

#       def compareContent (old_content: str, new_content: str) -> float:
#             difference = 0
#             for old_char, new_char in zip(old_content, new_content):
#                   if old_char != new_char:
#                         difference = difference +1

#             return difference / min(len(old_content), len(new_content))

#             """
#             old_content = old_content.splitlines()
#             new_content = new_content.splitlines()

#             difference = 0
#             for old_line, new_line in zip (old_content, new_content):
#                   difference = difference +compareLine(old_line, new_line)
            
#             if len(old_content) < len(new_content):
#                   for line in new_content[-len(new_content) +len(old_content):]:
#                         for word in line.split(' '):
#                               difference = difference +len(word)
#                   return difference / len(old_content)
#             else:
#                   for line in old_content[-len(old_content) +len(new_content):]:
#                         for word in line.split(' '):
#                               difference = difference +len(word)
#                   return difference / len(new_content)
#             """


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


# if __name__ == '__main__':
#       try:
#             main()
#       except KeyboardInterrupt:
#             print('Terminating')


