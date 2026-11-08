import base64, json, unittest
from unittest.mock import patch
import movie_helper as h

class HelperTests(unittest.TestCase):
    def test_movie_and_resource_parsing(self):
        page='<a title="搜索者 The Searchers" class="image" href="/movies/10046/"></a><a title="4K 中文字幕" href="/link_start/?seed_id=123&amp;movie_title=电影">link</a>'
        self.assertEqual(h.parse_links(page), [('搜索者 The Searchers','/movies/10046/'),('4K 中文字幕','/link_start/?seed_id=123&movie_title=电影')])
    def test_magnet_decode_and_reject_bad(self):
        m='magnet:?xt=urn:btih:'+'a'*40+'&dn=test'
        encoded=base64.b64encode(m.encode()).decode()
        self.assertEqual(h.parse_magnet('const data = "'+encoded+'";'),m)
        with self.assertRaises(ValueError):h.parse_magnet('const data="'+base64.b64encode(b'https://example.com').decode()+'"')
    def test_lan_restriction(self):
        self.assertEqual(h.private_ip('192.168.1.2'),'192.168.1.2')
        for v in ('8.8.8.8','127.0.0.1','169.254.1.1','example.org'):
            with self.assertRaises(ValueError):h.private_ip(v)
    def test_mock_nas_send(self):
        class R:
            status=200
            def __init__(self,x):self.x=x
            def read(self,n):return json.dumps(self.x).encode()
        class Fake:
            def __init__(self):self.calls=[]
            def request(self,*a,**kw):self.calls.append((a,kw))
            def getresponse(self):return R({'sid':'private-session'} if len(self.calls)==1 else {'error':0})
            def close(self):pass
        c=Fake(); m='magnet:?xt=urn:btih:'+'a'*40
        with patch.object(h,'connect_pinned',return_value=c):
            self.assertEqual(h.send_qnap('192.168.1.2',443,'b'*64,'user','password',[m],'下载','下载'),[True])
        self.assertEqual(c.calls[0][0][0],'POST');self.assertIn('/Task/AddUrl?',c.calls[1][0][1]);self.assertNotIn('password',c.calls[1][0][1])
    def test_wrong_fingerprint_rejected_before_login(self):
        class Sock:
            def getpeercert(self,**kw):return b'actual certificate'
        class Conn:
            def __init__(self,*a,**kw):self.sock=Sock();self.closed=False
            def connect(self):pass
            def close(self):self.closed=True
        with patch.object(h.http.client,'HTTPSConnection',Conn):
            with self.assertRaisesRegex(ValueError,'指纹不匹配'):h.connect_pinned('192.168.1.2',443,'0'*64)
if __name__=='__main__':unittest.main()
