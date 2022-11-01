
def main ():
      import sys, argparse, re, time, datetime

      def assertPositiveInt (value: str) -> int:
            try:
                  value = int(value)
            except ValueError:
                  raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
            if value < 0:
                  raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
            return value

      parser = argparse.ArgumentParser(description='''Checks a website continuously for updates and notifies the user when one occurs.''')
      parser.add_argument('url', type= str, help= 'the url of the website to check')
      parser.add_argument('-l', '--level', type= assertPositiveInt, help= 'checking level; 0 means only checking the supplied url, 1 means checking the supplied websites\' url and all of the urls that it has (such as links) and so on. The default is 0', default= 0)
      parser.add_argument('-t', '--threshold', type= assertPositiveInt, help= 'the threshold of change upon which the user is notified. It "can range" from 0 to infinity. The default is 0 (percent), where the user is notified if any change occurs', default= 0)
      parser.add_argument('-d' , '--delay', type= assertPositiveInt, help= 'the delay, in seconds, after every check. The default is 5 seconds', default= 5)
      parser.add_argument('-q', '--quiet', action= 'store_true', help= 'notify the user only about/when a change occurs')
      parser.add_argument('-c', '--crash', action= 'store_true', help= 'terminates the script if a website is unreachable or crashes')
      parser.add_argument('-i', '--ignore', type= str, nargs= '+', help= 'websites to ignore by default. Default includes: facebook, google, twitter and youtube', default= ['facebook', 'google', 'twitter', 'youtube'])

      args = parser.parse_args()


      try:
            import requests
      except ImportError:
            sys.exit('The requests package is missing.. Please consult the README file')
      try:
            import regex
      except ImportError:
            sys.exit('The regex package is missing.. Please consult the README file')


      def cleanContent (content: str) -> str:
            match = re.search(r'<\s*?body(.|\s)*?>(.|\s)*?<\s*?\/\s*?body\s*?>', content) # <body> ... </body>
            if not match:
                  return None

            content = match.group()

            for tag in ["class", "style", "id"]: # class=" ... "
                  regex = re.compile(tag +'\s*?=\s*?"(.|\s)*?"')
                  content = regex.sub('', content)

            for tag in ["link", "meta"]: # <link ... >
                  regex = re.compile('<\s*?' +tag +'(.|\s)*?>')
                  content = regex.sub('', content)

            for tag in ["link", "meta"]: # <link ... />
                  regex = re.compile('<\s*?' +tag +'(.|\s)*?\/\s*?>')
                  content = regex.sub('', content)

            for tag in ["script", "style", "link"]: # <script> ... </script>
                  regex = re.compile('<\s*?' +tag +'\s*?(.|\s)*?>(.|\s)*?<\s*?\/\s*?' +tag +'\s*?>')
                  content = regex.sub('', content)

            content = re.sub(r'data\s*?\-(.|\s)*?=\s*?"(.|\s)*?"', '', content) # data-... ...= "..."

            content = re.sub(r'<\s*?input.*?type\s*?=\s*?"hidden".*?>', '', content, flags= re.S) # <input ... type= "hidden">

            return content

      def getContent (url: str) -> str:
            if not url.startswith('http://') and not url.startswith('https://'):
                  url = 'http://' +url

            try:
                  headers = {"Accept-Language": "en"}
                  response = requests.get(url, headers= headers)

                  if response.status_code != 200:
                        return None

                  if not response.headers['Content-Type'].startswith('text/html'):
                        return None

                  return cleanContent(response.text)

            except requests.exceptions.RequestException:
                  return None

      def isIgnored (url: str) -> bool:
            for ignored in args.ignore:
                  if url.find(ignored) != -1:
                        return True
            return False

      def addAnchorsContent (content: str, contents: dict) -> bool:
            urls = regex.findall(r'(?<=<\s*?a[.\s]*?href\s*?=\s*?").*?(?=")', content)
            if not urls:
                  return False

            added = False
            for url in urls:
                  if url not in contents.keys() and not isIgnored(url):
                        anchor_content = getContent(url)
                        if anchor_content:
                              contents [url] = anchor_content
                              added = True
            return added


      def compareWord (old_word: str, new_word: str) -> str:
            difference = 0
            for old_char, new_char in zip(old_word, new_word):
                  if old_char != new_char:
                        difference = difference +1
            
            if len(old_word) < len(new_word):
                  difference = difference +len(new_word) -len(old_word)
                  return difference / len(old_word)
            else:
                  difference = difference +len(old_word) -len(new_word)
                  return difference / len(new_word)

      def compareLine (old_line: str, new_line: str) -> float: # TODO: fix/proper solution to whitespace
            old_line = old_line.split()
            new_line = new_line.split()

            if len(old_line) == 0 and len(new_line) == 0:
                  return 0

            difference = 0
            for old_word, new_word in zip (old_line, new_line):
                  difference = difference +compareWord(old_word, new_word)
            
            if len(old_line) < len(new_line):
                  for word in new_line[-len(new_line) +len(old_line):]:
                        difference = difference +len(word)
                  return difference / len(old_line)
            else:
                  for word in old_line[-len(old_line) +len(new_line):]:
                        difference = difference +len(word)
                  return difference / len(new_line)

      def compareContent (old_content: str, new_content: str) -> float:
            difference = 0
            for old_char, new_char in zip(old_content, new_content):
                  if old_char != new_char:
                        difference = difference +1

            return difference / min(len(old_content), len(new_content))

            """
            old_content = old_content.splitlines()
            new_content = new_content.splitlines()

            difference = 0
            for old_line, new_line in zip (old_content, new_content):
                  difference = difference +compareLine(old_line, new_line)
            
            if len(old_content) < len(new_content):
                  for line in new_content[-len(new_content) +len(old_content):]:
                        for word in line.split(' '):
                              difference = difference +len(word)
                  return difference / len(old_content)
            else:
                  for line in old_content[-len(old_content) +len(new_content):]:
                        for word in line.split(' '):
                              difference = difference +len(word)
                  return difference / len(new_content)
            """


# -------------------------------------------------------------------


      print('Pinging', args.url, '...')

      main_content = getContent(args.url)
      if not main_content:
            sys.exit(f'Unable to reach/read {args.url}')
      contents = {args.url: main_content}

      for _ in range (args.level): # TODO: a better solution, also a one that allows infinite depth
            for content in contents.copy().values():
                  addAnchorsContent(content, contents)


      PING_DELAY = args.delay

      print(f'Checking {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]} {["continuously", "every second", "every " +str(PING_DELAY) +" seconds"][(PING_DELAY != 0) + ((PING_DELAY != 0) * (PING_DELAY != 1))]}:')
      for url in contents.keys():
            print('\t->', url)

      while True:
            if not args.quiet:
                  print('\nChecking...')
            
            total_difference = 0
            for url, content in contents.items():

                  new_content = getContent(url)
                  if new_content:
                        difference = compareContent(content, new_content)
                        total_difference = total_difference +difference

                        if not args.quiet:
                              print('\t',url,'->', str(difference *100) +'%', 'difference.')
                  else:
                        if args.crash:
                              print('\n\n',url,'-> failed to reach/read.')
                              print(f'\nTerminated at {datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}')
                              sys.exit(0)
                        elif not args.quiet:
                              print('\t',url,'-> failed to reach/read.')

            total_difference /= len(contents)
            total_difference *= 100
            if not args.quiet:
                  print('\n\t->',str(total_difference) +'%', 'total difference.')
            
            if total_difference > args.threshold:
                  print('\a')
                  print(f'\nA total change of {total_difference}% occurred at {datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")} in {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]}:')
                  for url in contents.keys():
                        print('\t->', url)
                  print('Terminating')

                  sys.exit(0)

            time.sleep(PING_DELAY)


if __name__ == '__main__':
      try:
            main()
      except KeyboardInterrupt:
            print('Terminating')
