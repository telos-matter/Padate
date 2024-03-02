#! /usr/bin/env python

import requests
import argparse
from html.parser import HTMLParser
from enum import Enum, auto
from time import time, strftime, sleep

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
    raise argparse.ArgumentTypeError(f'{value} must be a positive integer value, i.e. value >= 0.')

def check_strict_positive_int (value: str) -> int:
    '''Used in arg_parser only'''
    try:
        value = int(value)
        if value > 0:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f'{value} must be a strictly positive integer value, i.e. value > 0.')

# Add the arg parser arguments
arg_parser.add_argument('url', type=str, help='the url of the website to watch / check. For example: `www.foo.com`.')
arg_parser.add_argument('-d' , '--delay', type=check_positive_int, help='the delay, in seconds, to wait between each check. The default is 0 seconds.', default=0)
arg_parser.add_argument('-q', '--quiet', action='store_true', help="signal only important stuff to the user.")
arg_parser.add_argument('-c', '--crash', action='store_true', help='halt the process if the website is unreachable or unable to be parsed when watching.')
arg_parser.add_argument('-t', '--timeout', type=check_strict_positive_int, help='the maximum time, in seconds, to wait for a response from the website. The default is 30 seconds.', default=30)

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
    
    def __init__(self, url: str, *, struct_tol: int=2) -> None:
        '''
        - `url`: the url of this page
        - `struct_tol`: How wrong can the HTML structure be
        and still tolerate / parse it?
            - 0: no tolerance
            - 1: minor tolerance (paragraphs don't need to close for example)
            - 2: just parse it dude
        '''
        super().__init__(convert_charrefs=True)
        
        self.url              = url # The url of this page
        self.valid            = False # Have we gotten a valid response from this page and were we able to successfully parse it?
        self.status           = 'Yet to make request.' # A message indicating the current status
        self.problems_counter = 0 # How many problems have been encountered when parsing, regardless of tolerance level. problems_counter == 99
        self.title            = None # The pages' title
        self.content          = [] # The pages' content in the order it is encountered in
        
        self.__struct_tol      = struct_tol # How tolerant are we with the structure of the page?
        self.__section_count   = 0 # How many sections have we seen so far?
        self.__current_section = None # Which section are we currently parsing?
        self.__current_tag     = None # Which tag are we currently parsing?
        self.__tag_stack       = [] # A stack to handle nested tags
        
        try:
            # Try and make a request to the url
            response = requests.get(self.url, allow_redirects=True, timeout=ARGS.timeout)
            
            # See if response can be read
            if response.status_code == 200 and response.headers['Content-type'].startswith('text/html'):
                # Update status
                self.status = 'Yet to parse.'
                # If it can, start parsing
                self.feed(response.text)
                # If all went well then the page is valid
                self.valid = True
                # Update status accordingly
                if self.problems_counter == 0:
                    self.status = 'All OK.'
                else:
                    self.status = 'OK.'
            # If it cannot be read then just update the status
            else:
                if response.status_code != 200:
                    self.status = f'Page responded with code `{response.status_code}` and not `200`.'
                else:
                    self.status = f"Page's content-type is {response.headers['Content-type']} and not `text/html`."
        
        except AssertionError as assertion:
            raise assertion
        except requests.exceptions.RequestException as e:
            self.status = f"Couldn't make a request because of this error: `{e}`."
        except Exception as e:
            self.status = f"Couldn't parse the page because of this error: `{e}`."
    
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
                    raise Exception(f"Was not expecting to encounter <head> here. line: {line}, col: {col}.")
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
    
    def __eq__(self, other: object) -> bool:
        '''Checks for equality based on title and content'''
        assert isinstance(other, Page) and self.url == other.url, f"Comparing different pages. {self} VS {other}"
        return self.title == other.title and self.content == other.content
    
    def __str__(self) -> str:
        return f"Page(url: {self.url}, title: {self.title}, content: {self.content})"
    
    def __repr__(self) -> str:
        return self.__str__()

def now () -> str:
    '''Returns the current time in the format of `YYYY-MM-DD HH:MM:SS AM/PM`'''
    return strftime('%Y-%m-%d %I:%M:%S %p')

def difference (old: Page, new: Page) -> str:
    '''Indicates the difference between the 2 pages.'''
    assert old != new, f"Pages are still the same! {old} VS {new}"
    
    # Compare the titles
    if old.title != new.title:
        return f"the title: `{old.title}` -> `{new.title}`"
    
    # Compare the content
    for o, n in zip(old.content, new.content):
        if o != n:
            return f"this line: `{o}` -> `{n}`"
    assert len(old.content) != len(new.content), f"Different pages but same content?! {old} VS {new}"
    if len(old.content) > len(new.content):
        return f"removing this line `{old.content[len(new.content)]}`"
    else:
        return f"adding this line `{new.content[len(old.content)]}`"

# Prepare the url
URL = ARGS.url
if not URL.startswith('http://') and not URL.startswith('https://'):
    URL = 'http://' +URL

# Try to make first connection
print(f"🛜 Pinging {URL}..")
ORIGINAL = Page(URL)

# If page is valid
if ORIGINAL.valid:
    # Say so and indicate that watching will start
    print(f"✅ Successfully retrieved `{ORIGINAL.title}`.")
    msg = None
    if ARGS.delay == 0:
        msg = f"🐕 Now watching the page continuously.."
    else:
        msg = f"⏲️  Now checking the page periodically every {[str(ARGS.delay) + ' seconds', 'second'][int(ARGS.delay == 1)]}.."
    print(msg)
    
    # Start watching
    while True:
        # Wait for given period
        sleep(ARGS.delay)
        
        # Make request
        if not ARGS.quiet:
            print(f"[{now()}] Checking {URL}..")
        page = Page(URL)
        # See if it's valid
        if page.valid:
            # If it was, compare the two pages
            if page != ORIGINAL:
                for _ in range(3):
                    print('\a')
                    sleep(.05)
                print(f"🔔 A change occurred in {URL}")
                for _ in range(3):
                    print('\a')
                    sleep(.05)
                # Indicate out what changed
                print(f"[{now()}] First apparent change is {difference(ORIGINAL, page)}.")
                break
            else:
                if not ARGS.quiet:
                    print(f"\t-> Apparently, nothing changed in `{page.title}`.")
        
        # If it's not valid
        else:
            # See if we should crash
            if ARGS.crash:
                print(f"❌ Couldn't check the page (REASON: {page.status})")
                break
            # Otherwise just say so if we can
            elif not ARGS.quiet:
                print(f"⛔️ Unable to check the page (REASON: {page.status})")
                print(f"🔁 Retrying..")

# Otherwise, if page is invalid, just say so
else:
    print(f"❌ Couldn't retrieve the page (REASON: {ORIGINAL.status}).")

# Record when the process finished and wait for the user to not be AFK
finished = time()
print(f"[{now()}] Press Enter when you are here..") # It's intentionally not in input. For better "UX"
input()
elapsed = time() - finished
if elapsed < 3:
    print(f"The process finished just now..")
else:
    # Formate elapsed time nicely
    hours = int(elapsed / 3600)
    hours = '' if hours == 0 else f"{hours} hour{'s'[:hours^1]}"
    minutes = int((elapsed % 3600) / 60)
    minutes = '' if minutes == 0 else f"{minutes} minute{'s'[:minutes^1]}"
    seconds = int(elapsed % 60)
    seconds = '' if seconds == 0 else f"{seconds} second{'s'[:seconds^1]}"
    time_stamp = [t for t in [hours, minutes, seconds] if t]
    assert len(time_stamp) != 0, f"Huh? {elapsed} seconds?"
    if len(time_stamp) == 1:
        time_stamp = time_stamp[0]
    elif len(time_stamp) == 2:
        time_stamp = ' and '.join(time_stamp)
    elif len(time_stamp) == 3:
        time_stamp = ', '.join(time_stamp[:-1]) + f" and {time_stamp[-1]}"
    else:
        assert False, f"Unreachable"
    
    print(f"The process finished {time_stamp} ago..")
