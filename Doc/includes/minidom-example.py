import xml.dom.minidom

document = "<slideshow>\n<title>Demo slideshow</title>\n<slide><title>Slide title</title>\n<point>This is a demo</point>\n<point>Of a program for processing slides</point>\n</slide>\n\n<slide><title>Another demo slide</title>\n<point>It is important</point>\n<point>To have more than</point>\n<point>one slide</point>\n</slide>\n</slideshow>\n"
dom = xml.dom.minidom.parseString(document)


def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return "".join(rc)


def handleSlideshow(slideshow):
    print("<html>")
    handleSlideshowTitle(slideshow.getElementsByTagName("title")[0])
    slides = slideshow.getElementsByTagName("slide")
    handleToc(slides)
    handleSlides(slides)
    print("</html>")


def handleSlides(slides):
    for slide in slides:
        handleSlide(slide)


def handleSlide(slide):
    handleSlideTitle(slide.getElementsByTagName("title")[0])
    handlePoints(slide.getElementsByTagName("point"))


def handleSlideshowTitle(title):
    print(("<title>%s</title>" % getText(title.childNodes)))


def handleSlideTitle(title):
    print(("<h2>%s</h2>" % getText(title.childNodes)))


def handlePoints(points):
    print("<ul>")
    for point in points:
        handlePoint(point)
    print("</ul>")


def handlePoint(point):
    print(("<li>%s</li>" % getText(point.childNodes)))


def handleToc(slides):
    for slide in slides:
        title = slide.getElementsByTagName("title")[0]
        print(("<p>%s</p>" % getText(title.childNodes)))


handleSlideshow(dom)
