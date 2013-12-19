
import jpype
import requests
import socket
try:
    import cchardet as chardet
except ImportError:
    import chardet
import threading

socket.setdefaulttimeout(15)
lock = threading.Lock()

InputSource        = jpype.JClass('org.xml.sax.InputSource')
StringReader       = jpype.JClass('java.io.StringReader')
HTMLHighlighter    = jpype.JClass('de.l3s.boilerpipe.sax.HTMLHighlighter')
BoilerpipeSAXInput = jpype.JClass('de.l3s.boilerpipe.sax.BoilerpipeSAXInput')

class Extractor(object):
    """
    Extract text. Constructor takes 'extractor' as a keyword argument,
    being one of the boilerpipe extractors:
    - DefaultExtractor
    - ArticleExtractor
    - ArticleSentencesExtractor
    - KeepEverythingExtractor
    - KeepEverythingWithMinKWordsExtractor
    - LargestContentExtractor
    - NumWordsRulesExtractor
    - CanolaExtractor
    """
    extractor = None
    extractor_name = None
    source = None
    data = None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19'}

    def __init__(self, *args, **kwargs):

        if len(args) == 0:
            extractor = 'ArticleExtractor'
        elif len(args) == 1:
            extractor = args[0]
        else:
            raise Exception('Invalid extractor param')
        self.extractor_name = extractor

        if kwargs.get('url'):
            self.setUrl(kwargs['url'])
        elif kwargs.get('html'):
            self.setHtml(kwargs['html'])

        try:
            # make it thread-safe
            if threading.activeCount() > 1:
                if jpype.isThreadAttachedToJVM() == False:
                    jpype.attachThreadToJVM()
            lock.acquire()
            
            self.extractor = jpype.JClass(
                "de.l3s.boilerpipe.extractors." + self.extractor_name).INSTANCE
        finally:
            lock.release()


    def setUrl(self, url):
        response = requests.get(url, headers=self.headers)
        content_type = response.headers.get('content-type')
        if content_type.lower().startswith('text/html'):
            content_encoding = chardet.detect(response.content)['encoding']
            if response.encoding.lower() != content_encoding.lower():
                self.data = response.content.decode(content_encoding)
            else:
                self.data = response.text
        else:
            raise Exception('Invalid content type')


    def setHtml(self, html):
        self.data = html

    def process(self):
        if self.data is None:
            raise Exception('No text or url provided')
        reader = StringReader(self.data)
        self.source = BoilerpipeSAXInput(InputSource(reader)).getTextDocument()
        self.extractor.process(self.source)

    def getText(self):
        return self.source.getContent()
    
    def getHTML(self):
        highlighter = HTMLHighlighter.newExtractingInstance()
        return highlighter.process(self.source, self.data)
    
    def getImages(self):
        extractor = jpype.JClass(
            "de.l3s.boilerpipe.sax.ImageExtractor").INSTANCE
        images = extractor.process(self.source, self.data)
        jpype.java.util.Collections.sort(images)
        images = [
            {
                'src'   : image.getSrc(),
                'width' : image.getWidth(),
                'height': image.getHeight(),
                'alt'   : image.getAlt(),
                'area'  : image.getArea()
            } for image in images
        ]
        return images
