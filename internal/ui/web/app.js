const app = { schema:null, values:{}, secrets:{}, hosts:[], operators:new Set(), activeRun:null, token:sessionStorage.getItem('installerToken') || '' };
const $ = selector => document.querySelector(selector);
const all = selector => [...document.querySelectorAll(selector)];

async function api(path, options={}) {
  const headers = {...(options.headers || {}), 'Content-Type':'application/json'};
  if (app.token) headers.Authorization = `Bearer ${app.token}`;
  const response = await fetch(path, {...options, headers});
  const text = await response.text();
  let body; try { body = JSON.parse(text); } catch { body = {error:text || response.statusText}; }
  if (response.status === 401) $('#auth-dialog').showModal();
  if (!response.ok) throw new Error(body.error || (body.errors || []).map(item => `${item.field}: ${item.message}`).join('\n'));
  return body;
}

function showMessage(text, error=false) { const node=$('#message'); node.textContent=text; node.classList.toggle('error',error); node.classList.remove('hidden'); window.scrollTo({top:0,behavior:'smooth'}); }
function safePreview() { return {profile:$('#profile-name').value, values:app.values, hosts:app.hosts.map(({bmc_username,bmc_password,...host})=>host), operators:[...app.operators], secrets:Object.fromEntries(Object.keys(app.secrets).map(key=>[key,app.secrets[key]?'[CONFIGURED]':'']))}; }
function payload() { return {profile:$('#profile-name').value, values:app.values, secrets:app.secrets, hosts:app.hosts, operators:[...app.operators], vault_password:$('#vault-password').value}; }
function parseStructured(value) { if (!value.trim()) return {}; return JSON.parse(value); }
function fieldValue(field) { return field.group==='secrets' ? app.secrets[field.name] : app.values[field.name]; }
function setField(field,value) { (field.group==='secrets'?app.secrets:app.values)[field.name]=value; updateVisibility(); updatePreview(); }
function isVisible(field) { return !field.visible_when || Object.entries(field.visible_when).every(([key,value])=>Array.isArray(value)?value.includes(app.values[key]):app.values[key]===value); }

function createField(field, value, onChange) {
  const wrap=document.createElement('div'); wrap.className='field'; wrap.dataset.field=field.name;
  if (field.widget==='checkbox' || field.type==='boolean') {
    wrap.classList.add('checkbox-field'); const input=document.createElement('input'); input.type='checkbox'; input.checked=Boolean(value); input.id=`field-${field.name}`; input.onchange=()=>onChange(input.checked); const label=document.createElement('label'); label.htmlFor=input.id; label.textContent=field.label; wrap.append(input,label); return wrap;
  }
  const label=document.createElement('label'); label.textContent=field.label+(field.required?' *':'');
  let input;
  if (field.widget==='select') { input=document.createElement('select'); (field.options||[]).forEach(option=>input.add(new Option(option,option))); input.value=value??''; input.onchange=()=>onChange(input.value); }
  else if (field.widget==='yaml' || field.type==='array' || field.type==='object' || field.widget==='textarea') { input=document.createElement('textarea'); input.value=typeof value==='string'?value:JSON.stringify(value,null,2); input.onchange=()=>{try{onChange(field.widget==='textarea'?input.value:parseStructured(input.value));input.setCustomValidity('');}catch{input.setCustomValidity('Enter valid JSON (JSON is valid YAML).');input.reportValidity();}}; wrap.classList.add('full'); }
  else { input=document.createElement('input'); input.type=field.widget==='password'?'password':field.widget==='number'?'number':'text'; input.value=value??''; if(field.minimum!==undefined)input.min=field.minimum; if(field.pattern)input.pattern=field.pattern; input.oninput=()=>onChange(input.type==='number'?Number(input.value):input.value); }
  input.id=`field-${field.name}`; input.required=Boolean(field.required); label.htmlFor=input.id; wrap.append(label,input); const note=document.createElement('small'); note.textContent=`Source: ${field.source || 'host inventory'}${field.widget==='yaml'?' · Enter JSON; it is valid YAML.':''}`; wrap.append(note); return wrap;
}

function renderGroups() {
  const nav=$('#group-nav'), panels=$('#dynamic-panels'); nav.innerHTML=''; panels.innerHTML='';
  app.schema.groups.filter(group=>group.id!=='secrets').forEach((group,index)=>{
    const button=document.createElement('button'); button.className='nav-item'; button.dataset.panel=group.id; button.innerHTML=`<span>01</span> ${group.label}`; nav.append(button);
    const panel=document.createElement('section'); panel.id=`panel-${group.id}`; panel.className='panel hidden'; panel.innerHTML=`<div class="panel-heading"><div><p class="step">Step 01</p><h2>${group.label}</h2><p>Defaults are loaded from the repository and remain fully editable for this profile.</p></div></div><div class="field-grid"></div>`;
    app.schema.variables.filter(field=>field.group===group.id && field.widget!=='operators' && field.widget!=='profile').forEach(field=>panel.querySelector('.field-grid').append(createField(field,fieldValue(field),value=>setField(field,value)))); panels.append(panel);
    if(index===0) setTimeout(()=>showPanel(group.id),0);
  });
  const secretGroup=app.schema.groups.find(group=>group.id==='secrets');
  const button=document.createElement('button'); button.className='nav-item'; button.dataset.panel='secrets'; button.innerHTML=`<span>01</span> ${secretGroup.label}`; nav.append(button);
  const panel=document.createElement('section'); panel.id='panel-secrets'; panel.className='panel hidden'; panel.innerHTML='<div class="panel-heading"><div><p class="step">Step 01</p><h2>Credentials and secrets</h2><p>Values are never returned by the API and are written only to the encrypted Ansible Vault.</p></div></div><div class="field-grid"></div>';
  app.schema.variables.filter(field=>field.group==='secrets').forEach(field=>panel.querySelector('.field-grid').append(createField(field,fieldValue(field),value=>setField(field,value)))); panels.append(panel);
}

function renderHosts() {
  const list=$('#host-list'); list.innerHTML='';
  app.hosts.forEach((host,index)=>{ const card=document.createElement('article'); card.className='host-card'; card.innerHTML=`<div class="host-head"><h3>${host.name||`Host ${index+1}`}</h3><button class="remove-host">Remove</button></div><div class="host-fields"></div>`; card.querySelector('.remove-host').onclick=()=>{app.hosts.splice(index,1);renderHosts();updatePreview();};
    const nameField={name:'name',label:'Inventory host name',required:true}; card.querySelector('.host-fields').append(createField(nameField,host.name,value=>{host.name=value;card.querySelector('h3').textContent=value||`Host ${index+1}`;updatePreview();}));
    app.schema.host_fields.forEach(field=>card.querySelector('.host-fields').append(createField(field,host[field.name],value=>{host[field.name]=value;updatePreview();}))); list.append(card); });
}

function renderOperators() {
  const profile=$('#operator-profile'); profile.innerHTML='<option value="custom">custom</option>'; Object.keys(app.schema.profiles).forEach(name=>profile.add(new Option(name,name))); profile.value=app.values.day2_gitops_profile || 'custom';
  profile.onchange=()=>{app.values.day2_gitops_profile=profile.value;if(profile.value!=='custom') app.schema.profiles[profile.value].forEach(name=>app.operators.add(name));renderOperatorCards();updatePreview();};
  renderOperatorCards();
}
function renderOperatorCards() { const query=$('#operator-search').value.toLowerCase(); const list=$('#operator-list'); list.innerHTML=''; app.schema.operators.filter(item=>`${item.id} ${item.display_name} ${item.package}`.toLowerCase().includes(query)).forEach(item=>{ const label=document.createElement('label'); label.className=`operator-card ${app.operators.has(item.id)?'selected':''}`; const check=document.createElement('input'); check.type='checkbox'; check.checked=app.operators.has(item.id); check.onchange=()=>{check.checked?app.operators.add(item.id):app.operators.delete(item.id);renderOperatorCards();updatePreview();}; const text=document.createElement('span'); text.innerHTML=`<strong>${item.display_name}</strong><small>${item.official?'Red Hat official':'Ecosystem'} · ${item.channel||'catalog default'}</small><code>${item.package}</code>`; label.append(check,text); list.append(label); }); $('#operator-count').textContent=`${app.operators.size} selected`; }

function renderActions() { const select=$('#action'); Object.entries(app.schema.actions).forEach(([name,action])=>select.add(new Option(action.label,name))); select.onchange=updateAction; updateAction(); }
function updateAction(){const action=app.schema.actions[$('#action').value];$('#action-description').textContent=action.description;$('#confirmation').value='';$('#confirmation').disabled=!action.confirmation;$('#confirmation-help').textContent=action.confirmation?`Type ${action.confirmation} exactly to enable this action.`:'No confirmation is required for this action.';}
function updateVisibility(){app.schema.variables.forEach(field=>{const node=document.querySelector(`[data-field="${field.name}"]`);if(node)node.classList.toggle('hidden',!isVisible(field));});}
function updatePreview(){app.values.day2_gitops_enabled_operators=[...app.operators];$('#preview').textContent=JSON.stringify(safePreview(),null,2);}
function showPanel(name){all('.panel').forEach(panel=>panel.classList.add('hidden'));$(`#panel-${CSS.escape(name)}`)?.classList.remove('hidden');all('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.panel===name));}

async function validate(save=false){const invalid=$('main input:invalid,main textarea:invalid,main select:invalid');if(invalid){invalid.reportValidity();showMessage('Correct the highlighted field before validation.',true);return;}try{const result=await api(`/api/config/${save?'save':'validate'}`,{method:'POST',body:JSON.stringify(payload())});showMessage(save?'Profile saved and Ansible Vault created.':'Configuration is valid.');return result;}catch(error){showMessage(error.message,true);throw error;}}
async function startRun(){try{const input={action:$('#action').value,profile:$('#profile-name').value,confirmation:$('#confirmation').value};const run=await api('/api/runs',{method:'POST',body:JSON.stringify(input)});app.activeRun=run.id;$('#logs').textContent='';updateRun(run);$('#cancel').disabled=false;$('#download-report').disabled=false;streamRun(run.id);}catch(error){showMessage(error.message,true);}}
async function streamRun(id){const headers={};if(app.token)headers.Authorization=`Bearer ${app.token}`;const response=await fetch(`/api/runs/${id}/events`,{headers});if(!response.ok){showMessage('Unable to open execution stream.',true);return;}const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const blocks=buffer.split('\n\n');buffer=blocks.pop();for(const block of blocks){const line=block.split('\n').find(item=>item.startsWith('data: '));if(line){const event=JSON.parse(line.slice(6));$('#logs').textContent+=`${event.line}\n`;$('#logs').scrollTop=$('#logs').scrollHeight;}}}const detail=await api(`/api/runs/${id}`);updateRun(detail.run);$('#cancel').disabled=true;}
function updateRun(run){$('#run-status').textContent=run.status;$('#run-status').className=`status ${run.status}`;$('#run-id').textContent=run.id;$('#run-started').textContent=new Date(run.started_at).toLocaleString();$('#run-exit').textContent=run.exit_code??'—';}
async function restoreLatestRun(){const history=await api('/api/runs');if(!history.runs.length)return;const run=history.runs[0];app.activeRun=run.id;const detail=await api(`/api/runs/${run.id}`);updateRun(detail.run);$('#logs').textContent=detail.events.map(event=>event.line).join('\n')||'No output was recorded.';$('#download-report').disabled=false;if(run.status==='running'||run.status==='queued'){ $('#cancel').disabled=false; $('#logs').textContent=''; streamRun(run.id); }}
async function cancelRun(){if(!app.activeRun)return;try{await api(`/api/runs/${app.activeRun}/cancel`,{method:'POST',body:'{}'});}catch(error){showMessage(error.message,true);}}
async function initialize(){try{app.schema=await api('/api/schema');app.schema.variables.forEach(field=>{if(field.group==='secrets')app.secrets[field.name]='';else app.values[field.name]=structuredClone(field.default);});app.hosts=structuredClone(app.schema.host_defaults).map(host=>({...host,bmc_username:'',bmc_password:''}));(app.values.day2_gitops_enabled_operators||[]).forEach(name=>app.operators.add(name));renderGroups();renderHosts();renderOperators();renderActions();updateVisibility();updatePreview();await restoreLatestRun();$('#connection').textContent='Ready';$('#connection').className='status succeeded';}catch(error){$('#connection').textContent='Authentication required';$('#connection').className='status failed';}}

document.addEventListener('click',event=>{const item=event.target.closest('.nav-item');if(item)showPanel(item.dataset.panel);});
$('#auth-button').onclick=()=>$('#auth-dialog').showModal();$('#save-token').onclick=()=>{app.token=$('#api-token').value;sessionStorage.setItem('installerToken',app.token);setTimeout(()=>location.reload(),0);};
$('#add-host').onclick=()=>{app.hosts.push({name:`worker-${app.hosts.length}`,node_hostname:`worker-${app.hosts.length}`,node_role:'worker',bmc_type:'auto',bmc_endpoint:'https://',bmc_username:'',bmc_password:'',node_ipv4_address:'',installation_disk_id:'',disks_skip_formatting:[],assisted_host_api_overrides:{}});renderHosts();updatePreview();};
$('#operator-search').oninput=renderOperatorCards;$('#validate').onclick=()=>validate(false);$('#save').onclick=()=>validate(true);$('#run').onclick=startRun;$('#cancel').onclick=cancelRun;
$('#download-config').onclick=()=>download('installation-profile-preview.json',JSON.stringify(safePreview(),null,2));$('#download-report').onclick=async()=>{if(app.activeRun)download(`${app.activeRun}.json`,JSON.stringify(await api(`/api/runs/${app.activeRun}`),null,2));};
function download(name,content){const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([content],{type:'application/json'}));link.download=name;link.click();URL.revokeObjectURL(link.href);}
initialize();
