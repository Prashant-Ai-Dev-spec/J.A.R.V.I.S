(async function(){
  let localStream = null
  let peers = {} // username -> RTCPeerConnection
  let ws = null
  let recorder = null
  let recordedChunks = []

  const joinBtn = document.getElementById('join')
  const leaveBtn = document.getElementById('leave')
  const recordBtn = document.getElementById('record')

  async function loginAndToken(username, password){
    const res = await fetch('/login', {method:'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({username, password})})
    if (!res.ok) throw new Error('login failed')
    const data = await res.json()
    return data.access_token
  }

  function addVideo(username, stream){
    let v = document.getElementById('vid_'+username)
    if (!v){
      v = document.createElement('video')
      v.id = 'vid_'+username
      v.autoplay = true
      v.playsInline = true
      document.getElementById('videos').appendChild(v)
    }
    v.srcObject = stream
  }

  function removeVideo(username){
    const v = document.getElementById('vid_'+username)
    if (v){ v.srcObject = null; v.remove() }
  }

  async function createPeer(username, isInitiator, token){
    const pc = new RTCPeerConnection({iceServers: [{urls: 'stun:stun.l.google.com:19302'}]})
    pc.onicecandidate = (e) => {
      if (e.candidate) ws.send(JSON.stringify({type:'ice', to: username, data: e.candidate}))
    }
    pc.ontrack = (e) => addVideo(username, e.streams[0])
    if (localStream) {
      localStream.getTracks().forEach(t => pc.addTrack(t, localStream))
      addVideo('me', localStream)
    }
    peers[username] = pc
    return pc
  }

  joinBtn.onclick = async () => {
    const room = document.getElementById('room').value
    const username = document.getElementById('username').value
    const password = document.getElementById('password').value
    const token = await loginAndToken(username, password)
    try { localStream = await navigator.mediaDevices.getUserMedia({audio:true, video:true}) } catch(e){ alert('getUserMedia failed: '+e); return }
    ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws/meet/' + encodeURIComponent(room))
    ws.onopen = () => {
      ws.send(JSON.stringify({type:'join', username: username}))
    }
    ws.onmessage = async (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.type === 'participants'){
        // create peers to all existing participants (we are initiator)
        for (const other of msg.participants){
          const pc = await createPeer(other, true, token)
          const offer = await pc.createOffer()
          await pc.setLocalDescription(offer)
          ws.send(JSON.stringify({type:'offer', to: other, data: offer}))
        }
        document.getElementById('controls').style.display = 'block'
      } else if (msg.type === 'join'){
        // a new user joined; create peer but wait for their offer
        // no action required immediately
      } else if (msg.type === 'offer'){
        const from = msg.from
        const pc = await createPeer(from, false, token)
        await pc.setRemoteDescription(msg.data)
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        ws.send(JSON.stringify({type:'answer', to: from, data: answer}))
      } else if (msg.type === 'answer'){
        const from = msg.from
        const pc = peers[from]
        if (pc) await pc.setRemoteDescription(msg.data)
      } else if (msg.type === 'ice'){
        const from = msg.from
        const pc = peers[from]
        if (pc) await pc.addIceCandidate(msg.data)
      } else if (msg.type === 'leave'){
        removeVideo(msg.username)
        if (peers[msg.username]){ peers[msg.username].close(); delete peers[msg.username] }
      }
    }

    leaveBtn.onclick = () => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({type:'leave'}))
      Object.values(peers).forEach(p=>p.close())
      peers = {}
      document.getElementById('controls').style.display = 'none'
    }

    recordBtn.onclick = () => {
      if (!recorder){
        recorder = new MediaRecorder(localStream)
        recordedChunks = []
        recorder.ondataavailable = e => { if (e.data && e.data.size) recordedChunks.push(e.data) }
        recorder.onstop = async () => {
          const blob = new Blob(recordedChunks, {type: 'video/webm'})
          const form = new FormData(); form.append('file', blob, 'meeting_recording.webm')
          // upload using fetch; requires user to be logged in
          const tokenHeader = {Authorization: 'Bearer ' + token}
          await fetch('/upload', {method:'POST', headers: tokenHeader, body: form})
          alert('Recording uploaded')
          recorder = null
        }
        recorder.start()
        recordBtn.textContent = 'Stop Recording'
      } else {
        recorder.stop()
        recordBtn.textContent = 'Start Recording'
      }
    }
  }
})();
