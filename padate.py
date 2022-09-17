try:
      import sys, argparse, re, time

      def assertPositiveInt (value: int) -> int:
            try:
                  value = int(value)
            except ValueError:
                  raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
            if value < 0:
                  raise argparse.ArgumentTypeError(f'{value} must be a positive int value.')
            return value

      parser = argparse.ArgumentParser(description='''Checks a website continuously for updates and notifies the user when one occurs.''')
      parser.add_argument('url', type= str, help= 'the url of the website to check')
      parser.add_argument('-t' , '--time', type= assertPositiveInt, help= 'the delay, in seconds, after every check. The default is 5 seconds.', default= 5)
      parser.add_argument('-q', '--quiet', action= 'store_true', help= 'notify the user ONLY about/when a change occurs')

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

            for tag in ["class"]: # class=" ... "
                  regex = re.compile(tag +'\s*?=\s*?"(.|\s)*?"')
                  content = regex.sub('', content)

            for tag in ["link"]: # <link ... >
                  regex = re.compile('<\s*?' +tag +'(.|\s)*?>')
                  content = regex.sub('', content)

            for tag in ["link"]: # <link ... />
                  regex = re.compile('<\s*?' +tag +'(.|\s)*?\/\s*?>')
                  content = regex.sub('', content)

            for tag in ["script", "style", "link"]: # <script> ... </script>
                  regex = re.compile('<\s*?' +tag +'\s*?(.|\s)*?>(.|\s)*?<\s*?\/\s*?' +tag +'\s*?>')
                  content = regex.sub('', content)

            return content

      def getContent (url: str, assertion_flag: bool= True) -> str:
            if not url.startswith('http://') and not url.startswith('https://'):
                  url = 'http://' +url

            try:
                  response = requests.get(url)

                  if not response.headers['Content-Type'].startswith('text/html'):
                        if assertion_flag:
                              sys.exit('This page: '+ url +' has changed its content format, rendering it unable to be read') # TODO: use formater
                        else:
                              return None

                  content = cleanContent(response.text)
                  if assertion_flag and not content:
                        sys.exit('This page: '+ url +' has changed its content format, rendering it unable to be read')
                  return content

            except requests.exceptions.ConnectionError:
                  return None if not assertion_flag else sys.exit('Unable to connect to: '+ url)
            except requests.exceptions.RequestException as e:
                  return None if not assertion_flag else sys.exit('Connection error occured while trying to connect to: ' +url +'\nError: ' +type(e).__name__)

      def getAnchorsContent (content: str) -> dict:
            urls = regex.findall(r'(?<=<\s*?a[.\s]*?href\s*?=\s*?").*?(?=")', content)
            if not urls:
                  return {}

            contents = {}
            for url in urls:
                  if url not in contents.keys():
                        anchor_content = getContent(url, False)
                        if anchor_content:
                              contents [url] = anchor_content
            return contents

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

      if not args.quiet:
                  print('Checking', args.url, '...')

      main_content = getContent(args.url, True)
      contents = {args.url: main_content}
      for url, content in getAnchorsContent(main_content).items():
            contents [url] = content

      PING_DELAY = args.time

      if not args.quiet:
            print(f'Checking {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]} {["continuously", "every second", "every " +str(PING_DELAY) +" seconds"][(PING_DELAY != 0) + ((PING_DELAY != 0) * (PING_DELAY != 1))]}:')
            for url in contents.keys():
                  print('\t->', url)

      while True:
            if not args.quiet:
                  print('\nChecking...')
            
            total_difference = 0
            for url, content in contents.items():
                  difference = compareContent(content, getContent(url, True))
                  total_difference = total_difference +difference

                  if not args.quiet:
                        print('\t',url,'->', str(difference) +'%', 'difference.')
            
            total_difference = total_difference / len(contents)
            if not args.quiet:
                  print('\t',str(total_difference) +'%', 'total difference.')
            
            if total_difference > 0.05:
                  print(f'\nA change of {total_difference}% occured in {["this", "these " +str(len(contents))][len(contents) != 1]} website{"s"[:len(contents) != 1]}:')
                  for url in contents.keys():
                        print('\t->', url)

                  sys.exit(0)

            time.sleep(PING_DELAY)


except KeyboardInterrupt:
      sys.exit(0)
