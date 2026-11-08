const H={'Access-Control-Allow-Origin':'https://laolu-md.github.io','Access-Control-Allow-Headers':'authorization, apikey, content-type, x-client-info','Access-Control-Allow-Methods':'POST, OPTIONS','Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'};
const reply=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:H});
Deno.serve(async(req:Request)=>{
if(req.method==='OPTIONS')return new Response(null,{status:204,headers:H});
if(req.method!=='POST')return reply({error:'Method not allowed'},405);
try{
const auth=req.headers.get('authorization')||'';
let sub='';try { const payload=auth.replace(/^Bearer\s+/i,'').split('.')[1].replace(/-/g,'+').replace(/_/g,'/');sub=JSON.parse(atob(payload)).sub||'' } catch {}
if(sub!=='45572a09-18ba-4d66-8b3c-684b70d5cc9e') return reply({error:'无权访问'},403);
const body=await req.json(); const {action,value}=body;
if(!['search','versions','magnet'].includes(action)||typeof value!=='string'||value.length>300)return reply({error:'无效请求'},400);
let path='';
if(action==='search'){if(!value.trim())return reply({error:'请输入影片名'},400);path='/s/'+encodeURIComponent(value.trim())+'/';}
if(action==='versions'){if(!/^\/movies\/\d+\/?$/.test(value))return reply({error:'影片地址无效'},400);path=value;}
if(action==='magnet'){const u=new URL(value,'https://www.seedhub.cc');if(u.origin!=='https://www.seedhub.cc'||u.pathname!=='/link_start/'||!/^\d+$/.test(u.searchParams.get('seed_id')||''))return reply({error:'资源地址无效'},400);path=u.pathname+u.search;}
const response=await fetch('https://www.seedhub.cc'+path,{headers:{'User-Agent':'Mozilla/5.0 (compatible; MovieList/1.0)'},redirect:'manual',signal:AbortSignal.timeout(15000)});
if(!response.ok)return reply({error:'SeedHub 暂时拒绝访问（HTTP '+response.status+'）'},502);
const html=await response.text();if(html.length>3000000)return reply({error:'页面过大'},502);
if(/Just a moment|Checking your browser/i.test(html))return reply({error:'SeedHub 要求浏览器验证'},502);
const decode=(s:string)=>s.replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
if(action==='magnet'){
const match=html.match(/\b(?:const|let|var)\s+data\s*=\s*["']([A-Za-z0-9+/=]+)["']/);
let magnet='';try{if(match)magnet=atob(match[1]);}catch{}
if(!/^magnet:\?xt=urn:btih:[a-z0-9]{32,40}(?:&|$)/i.test(magnet))return reply({error:'无法识别此资源的磁力链接'},502);
return reply({magnet});
}
let items=[];let seen=new Set();for(const m of html.matchAll(/<a\b([^>]+)>/gi)){
const attrs=m[1],hm=attrs.match(/\bhref\s*=\s*["']([^"']+)["']/i),tm=attrs.match(/\btitle\s*=\s*["']([^"']+)["']/i);if(!hm)continue;const href=decode(hm[1]); const title=decode(tm?.[1]||'');
if(action==='search'&&/^\/movies\/\d+\/?$/.test(href)&&title&&!seen.has(href)){items.push({title,path:href});seen.add(href)}
if(action==='versions'&&href.startsWith('/link_start/')&&new URL(href,'https://www.seedhub.cc').searchParams.has('seed_id')&&!seen.has(href)){items.push({title:title||'未命名资源',path:href});seen.add(href)}
if(items.length>=100)break;
}
return reply({items});
}catch(e){return reply({error:'查询失败，请稍后重试'},502)}
});