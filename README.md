# Padate 

A utility python script that checks a website continuously for updates and notifies the user when one occurs. Useful when waiting for school results, job opportunity or wanting to be first on an event...


### Example:
Let's say you want to be the first to see PewDiePies' newest video:
1. Copy the channel link
2. Open up your command line / terminal
3. Run the following: `python path_to_padate.py https://www.youtube.com/PewDiePie`

And that's it! Leave the script running in the background and it would notify you with a *ding* sound once a change occurs.

You can tweak certain options before running the script, such as:
* How fast should the script check:
	`python path_to_padate.py url_to_check.com -d 0`
* How deep should the script check:
	`python path_to_padate.py url_to_check.com -l 1`
* Websites to ignore (useful when the website you are interested in has links to other websites):
	`python path_to_padate.py url_to_check.com -i facebook twitter`

and others.. Use help for more informations:
`python path_to_padate.py -h`

You can always quit the script with ctrl +c

### Requirements:
* Python 3.10 +
* The package requests 2.28.1 +
* The package regex  2022.9.13 +
### How-to:
You can make sure you have python 3 and above by running: `python --version`

Make sure you have pip installed (or any python package manager), and run the following in your command line/terminal: `pip install requests` and `pip install regex`

If you don't have python or pip installed, then look it up online with your operating system specified.

### /!\ Notice /!\
The script is not always reliable, as that not all pages follow an **exact** format. And it can also sometimes false trigger.. You can read more about why this happens on the technical part below.

### Technical part:
Dev not smart
Twitter's an ass
><div ><a href="https://www.facebook.com/recover/initiate/?privacy_mutation_token=eyJ0eXBlIjowLCJjcmVhdGlvbl90aW1lIjoxNjYzNDYwMzQ4LCJjYWxsc2l0ZV9pZCI6MzgxMjI5MDc5NTc1OTQ2fQ%3D%3D&amp;ars=facebook_login">Mot de passe oublié ?</a></di

 ><a href="https://www.facebook.com/recover/initiate/?privacy_mutation_token=eyJ0eXBlIjowLCJjcmVhdGlvbl90aW1lIjoxNjYzNDYwMzQ5LCJjYWxsc2l0ZV9pZCI6MzgxMjI5MDc5NTc1OTQ2fQ%3D%3D&amp;ars=facebook_login">Mot de passe oublié ?</a><
