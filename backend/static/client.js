let ACCESS_TOKEN = null
let WS = null

async function refreshFileList() {
  if (!ACCESS_TOKEN) return
  const res = await fetch('/files', {headers: {Authorization: 'Bearer ' + ACCESS_TOKEN}})
  const data = await res.json()
  const ul = document.getElementById('files')
  ul.innerHTML = ''
  data.files.forEach(f => {
    const li = document.createElement('li')
    const a = document.createElement('a')
    a.href = `/files/${f.id}`
    a.textContent = f.filename
    li.appendChild(a)
    ul.appendChild(li)
  })
}

document.getElementById('login').onclick = async () => {
  const u = document.getElementById('username').value
  const p = document.getElementById('password').value
  const res = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})})
  const data = await res.json()
  ACCESS_TOKEN = data.access_token
  const token = ACCESS_TOKEN
  if (!token) { alert('Login failed'); return }
  document.getElementById('chat').style.display = 'block'
  const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://'
  WS = new WebSocket(`${protocol}${location.host}/ws/chat?token=${token}`)
  WS.onmessage = (ev) => {
    try {
      const m = JSON.parse(ev.data)
      const el = document.createElement('div')
      el.textContent = m.username + ': ' + m.content
      document.getElementById('messages').appendChild(el)
    } catch (e) {
      const el = document.createElement('div')
      el.textContent = ev.data
      document.getElementById('messages').appendChild(el)
    }
  }
  document.getElementById('send').onclick = () => {
    const text = document.getElementById('msg').value
    WS.send(text)
    document.getElementById('msg').value = ''
  }
  document.getElementById('upload').onclick = async () => {
    const fi = document.getElementById('fileinput')
    if (fi.files.length === 0) return alert('Choose a file')
    const form = new FormData()
    form.append('file', fi.files[0])
    const up = await fetch('/upload', {method: 'POST', headers: {Authorization: 'Bearer ' + ACCESS_TOKEN}, body: form})
    if (up.ok) { alert('Uploaded'); refreshFileList() } else { alert('Upload failed') }
  }
  await refreshFileList()
}
