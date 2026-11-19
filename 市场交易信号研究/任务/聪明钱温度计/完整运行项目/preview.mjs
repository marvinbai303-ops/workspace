import http from 'node:http';
import worker from './worker/index.js';
http.createServer(async(req,res)=>{try{const request=new Request('http://127.0.0.1:8765'+req.url,{method:req.method});const r=await worker.fetch(request,{});res.writeHead(r.status,Object.fromEntries(r.headers));res.end(Buffer.from(await r.arrayBuffer()));}catch(e){res.writeHead(500);res.end(e.message)}}).listen(8765,'127.0.0.1',()=>process.stdout.write('Local: http://127.0.0.1:8765\n'));
