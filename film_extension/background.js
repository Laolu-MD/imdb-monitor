function decode(s){return s.replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>')}
async function run(action,value){
if(action==='ping')return {ready:true};
let path='';
if(action==='search'){if(!value.trim())throw Error('请输入影片名');path='/s/'+encodeURIComponent(value.trim())+'/';}
else if(action==='versions'){if(!/^\/movies\/\d+\/?$/.test(value))throw Error('影片地址无效');path=value}
else if(action==='magnet'){let u=new URL(value,'https://www.seedhub.cc');if(u.origin!=='https://www.seedhub.cc'||u.pathname!=='/link_start/'||!/^\d+$/.test(u.searchParams.get('seed_id')||''))throw Error('资源地址无效');path=u.pathname+u.search}
else throw Error('无效操作');
let r=await fetch('https://www.seedhub.cc'+path,{credentials:'include',redirect:'error',signal:AbortSignal.timeout(20000)});
if(!r.ok)throw Error('SeedHub 拒绝访问（HTTP '+r.status+'），请先在浏览器正常打开 SeedHub 后重试');
let html=await r.text();if(html.length>3000000)throw Error('页面过大');if(/Just a moment|Checking your browser/i.test(html))throw Error('请先在浏览器正常打开 SeedHub 并完成网站验证');
if(action==='magnet'){
let match=html.match(/\b(?:const|let|var)\s+data\s*=\s*["']([A-Za-z0-9+/=]+)["']/),m='';try{if(match)m=atob(match[1]);}catch{}
if(!/^magnet:\?xt=urn:btih:(?:[a-f0-9]{40}|[a-z2-7]{32})(?:&|$)/i.test(m))throw Error('无法读取此资源的磁力链接');return {magnet:m};
}
let items=[],seen=new Set();for(const m of html.matchAll(/<a\b([^>]+)>/gi)){let attrs=m[1],h=attrs.match(/\bhref\s*=\s*["']([^"']+)["']/i),t=attrs.match(/\btitle\s*=\s*["']([^"']+)["']/i);if(!h)continue;let path=decode(h[1]),title=decode(t?.[1]||'');if(action==='search'&&!/^\/movies\/\d+\/?$/.test(path))continue;if(action==='search'&&!title)continue;if(action==='versions'&&(!path.startsWith('/link_start/')||!/^\d+$/.test(new URL(path,'https://www.seedhub.cc').searchParams.get('seed_id')||'')))continue;if(seen.has(path))continue;seen.add(path);items.push({title:title||'未命名资源',path});if(items.length>=100)break;}
return {items};
}
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{try{let u=new URL(sender.url);if(u.origin!=='https://laolu-md.github.io'||!u.pathname.startsWith('/imdb-monitor/'))throw Error('来源无权访问');if(!message||!['ping','search','versions','magnet'].includes(message.action)||typeof message.value!=='string'||message.value.length>300)throw Error('请求无效');run(message.action,message.value).then(sendResponse,e=>sendResponse({error:e.message||'查询失败'}));}catch(e){sendResponse({error:e.message||'请求无效'})}return true;});