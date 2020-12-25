# ceterach

[![Documentation Status](https://readthedocs.org/projects/ceterach/badge/?version=latest)](http://ceterach.readthedocs.io/?badge=latest)

Rather than attempting the impossible task of being a full service,
e.g. [EarwigBot](http://github.com/earwig/earwigbot/), ceterach aims to be a
simple modular toolkit. ceterach tries to strike the balance between being a
fully featured package and being a light interface to MediaWiki, leading it
to be as capable as it is of standing alone as it is of fitting seamlessly
alongside other Python code.

ceterach emphatically aims to be a general MediaWiki interface, not a
Wikipedia-centric one. Wikipedia-specific functionality can be added by
creating extensions, a process that is as of yet undocumented and left as an
exercise to the reader.

### Examples

The following short program demonstrates manipulating the text of a Wikipedia
article:

```python
from ceterach.api import MediaWiki

api = MediaWiki("http://en.wikipedia.org/w/api.php")
api.login(username, password)
p = api.page("Wikipedia")
if p.exists:
    text = p.content.replace("Jimmy Wales", "[[User:Jimbo Wales]]")
    summary = "Replaced Jimmy with his username"
    p.edit(text, summary, minor=True)
api.logout()
```

The following short program deletes the talk pages of pages (not recursing
into subcategories) of a category, except for the page on Napoleon:

```python

from ceterach.api import MediaWiki

api = MediaWiki("http://en.wikipedia.org/w/api.php")
api.login(username, password)

catname = input("What's the category? Do not enter the 'Category:' prefix: ")
c = api.category("Category:" + catname)
for p in c.members:
    if p.title == "Napoleon":
        print("Found Napoleon! Skipping...")
        continue
    if not p.is_talkpage:
        p = p.toggle_talk() 
    p.delete("Hasta la vista")
api.logout()
```

The following short program emails everyone who edited the article on Napoleon:

```python
from ceterach.api import MediaWiki

api = MediaWiki("http://en.wikipedia.org/w/api.php")
api.login(username, password)

p = api.page("Napoleon Bonaparte", follow_redirects=True)
# any action performed on p will be equivalent to working on the "Napoleon"
# page but resolution of redirects is lazy! Since we're told that the title
# is "Napoleon Bonaparte", we won't try to resolve redirects until we try to
# interact with the API using that title:
assert p.title == "Napoleon Bonaparte"
p.load_attributes()  # We can force page normalisation by calling this method
assert p.title == "Napoleon"

# You can set the follow_redirects parameter to False to ensure that you don't
# follow redirects:
p2 = api.page("Napoleon Bonaparte", follow_redirects=False)
p2.load_attributes()
assert p2.is_redirect
print(p2.content)  # prints '#REDIRECT [[Napoleon]] {{R from other name}}'
del p2

for r in p.revisions:  # p.revisions[n] is newer than p.revisions[n+1]
    u = r.user
    if u.is_emailable:
        subject = "Regarding your edit on Napoleon"
        if r.is_minor:
            subject = subject.replace("your edit", "your minor edit")
        body = "I saw revision number {}. Nice edit! Unless it was vandalism."
        body = body.format(r.revid)
        u.email(subject, body, cc=False)  # Don't spam myself lol
api.logout()
```
