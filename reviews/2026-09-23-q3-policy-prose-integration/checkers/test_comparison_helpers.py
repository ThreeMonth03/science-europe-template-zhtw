"""Mutation tests for strict equivalence; generated values only."""
import io,unittest,zipfile
import check

CORE=b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dcterms="http://purl.org/dc/terms/"><dcterms:created>one</dcterms:created><dcterms:modified>two</dcterms:modified><cp:revision>1</cp:revision></cp:coreProperties>'
def archive(values):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for name,value in values.items():z.writestr(name,value)
    stream.seek(0);return stream
def bbox(words='<word xMin="1" yMin="1" xMax="2" yMax="2">x</word>'):
    return ('<html><body><page width="10" height="10">'+words+'</page></body></html>').encode()
class Checks(unittest.TestCase):
    def test_only_core_timestamps_ignored(self):
        a={'docProps/core.xml':CORE,'word/document.xml':b'<test>original</test>'}
        b=dict(a);b['docProps/core.xml']=CORE.replace(b'>one<',b'>different<')
        check.word_pair(archive(a),archive(b))
        b['docProps/core.xml']=CORE.replace(b'>1<',b'>2<')
        with self.assertRaises(AssertionError):check.word_pair(archive(a),archive(b))
    def test_docx_content_mutation(self):
        a={'docProps/core.xml':CORE,'word/document.xml':b'original'};b=dict(a);b['word/document.xml']=b'missing'
        with self.assertRaises(AssertionError):check.word_pair(archive(a),archive(b))
    def test_docx_extra_member(self):
        a={'docProps/core.xml':CORE};b=dict(a,unexpected=b'x')
        with self.assertRaises(AssertionError):check.word_pair(archive(a),archive(b))
    def test_no_pdf_pages(self):
        with self.assertRaises(AssertionError):check.geometry(b'<html><body/></html>')
    def test_blank_pdf_page(self):
        with self.assertRaises(AssertionError):check.geometry(bbox(''))
    def test_offpage_pdf_text(self):
        check.geometry(bbox())
        with self.assertRaises(AssertionError):check.geometry(bbox().replace(b'xMax="2"',b'xMax="12"'))
    def test_nonfinite_pdf_coordinates(self):
        with self.assertRaises(AssertionError):check.geometry(bbox().replace(b'yMin="1"',b'yMin="nan"'))
    def test_html_content_loss(self):
        with self.assertRaises(AssertionError):check.html_pair(b'<p>answer</p>',b'<p/>','submission')
    def test_identical_html_without_questions(self):
        with self.assertRaises(AssertionError):check.html_pair(b'<p>answer</p>',b'<p>answer</p>','submission')
if __name__=='__main__':unittest.main()
