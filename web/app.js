let id=sessionStorage.chatUser||'';
let session=sessionStorage.chatSession||'';
let seen=new Set();
let events=null;
const msgs=document.getElementById('msgs');
const state=document.getElementById('state');

function add(text,cssClass,key){
  if(key&&seen.has(key))return;
  if(key)seen.add(key);
  const node=document.createElement('div');
  node.className='m '+cssClass;
  node.textContent=text;
  msgs.appendChild(node);
  msgs.scrollTop=msgs.scrollHeight;
}

async function ensureSession(){
  if(id)return;
  const response=await fetch('/web/session',{method:'POST',credentials:'same-origin'});
  if(!response.ok)throw new Error('session');
  const data=await response.json();
  id=data.user_id;
  sessionStorage.chatUser=id;
}

function connectEvents(){
  if(!session)return;
  if(events)events.close();
  const url='/web/conversations/'+encodeURIComponent(session)+'/events?user_id='+encodeURIComponent(id);
  events=new EventSource(url,{withCredentials:true});
  events.addEventListener('message',event=>{
    const message=JSON.parse(event.data);
    if(message.role==='agent')add(message.text,'a',message.id);
  });
  events.onopen=()=>{state.textContent='AI assistant · secure live session';};
  events.onerror=()=>{state.textContent='Live reconnecting…';};
}

async function poll(){
  if(!session)return;
  try{
    const response=await fetch('/web/conversations/'+encodeURIComponent(session)+'/messages?user_id='+encodeURIComponent(id),{credentials:'same-origin'});
    if(!response.ok)return;
    const data=await response.json();
    for(const message of data){
      if(message.role==='agent')add(message.text,'a',message.id);
    }
  }catch{}
}

document.getElementById('form').addEventListener('submit',async event=>{
  event.preventDefault();
  const input=document.getElementById('input');
  const text=input.value.trim();
  if(!text)return;
  add(text,'u');
  input.value='';
  try{
    await ensureSession();
    const response=await fetch('/webhook/web',{
      method:'POST',
      credentials:'same-origin',
      headers:{'content-type':'application/json'},
      body:JSON.stringify({channel:'web_chat',user_id:id,text})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'request');
    session=data.session_id;
    sessionStorage.chatSession=session;
    state.textContent=data.conversation_status==='WAITING_FOR_AGENT'?'Waiting for a human agent…':'AI assistant · secure live session';
    add(data.reply||'Something went wrong.','b');
    connectEvents();
  }catch{
    add('Unable to reach support right now.','b');
  }
});

(async()=>{
  try{
    await ensureSession();
    connectEvents();
    await poll();
  }catch{
    state.textContent='Unable to establish secure session';
  }
})();

setInterval(()=>{
  if(!events||events.readyState===EventSource.CLOSED)poll();
},5000);
