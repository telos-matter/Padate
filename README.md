# Padate &nbsp; ![DEVELOPMENT STATUS: finished](https://badgen.net/badge/DEVELOPMENT%20STATUS/finished/green)
**Pa**ge Up**date**r

A utility python script that checks a website periodically for updates and notifies the user when one occurs.

Useful when waiting for results, new posts, or wanting to be first on an event for example...

## Example:
Supposedly you want to be notified when I add a new repository to my github account, you'd simply copy the link and run [padate.py](padate.py) with the link as an argument, like so:
```console
$ ./padate.py 'github.com/telos-matter?tab=repositories'
```

And that's it! Leave the script running and it would notify you with a *ding* sound once a change occurs.

There are certain options you can tweak, check them out with the help command:
```console
$ ./padate.py -h
```

## Requirements:
- Python 3.10 +
- The [requests](https://pypi.org/project/requests/) library 2.31 + ```pip install requests```

## ⚠️ Notice
The script is not always reliable, as that not all pages follow an **exact** format. And some of them don't even allow for an easy way to retrieve the visible data. So don't use this for anything critical, like a job application or something.

## How it works:
The scripts makes a request to the given URL and only saves the visible HTML content, that is text, paragraphs, headers, etc... (not images tho 💀). Then it makes a new request and checks its content with the saved one, and if they differ, it notifies the user.

Reason why it doesn't simply just compare the two requests is because some pages have dynamic content, like tokens, or meta data for example. And that would cause the script to notify the user even if the page didn't change in a meaningful way.

Feel free to implement a check for images too..
