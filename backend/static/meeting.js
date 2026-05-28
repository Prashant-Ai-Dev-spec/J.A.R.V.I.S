(async function(){
  const room = 'default_room';
  const ws = new WebSocket(`ws://${location.host}/ws/meet/${room}`);
  let pc;
  const local = document.getElementById('localVideo');
  const remote = document.getElementById('remoteVideo');

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
    local.srcObject = stream;
    pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    stream.getTracks().forEach(t=>pc.addTrack(t, stream));
    pc.ontrack = e => { remote.srcObject = e.streams[0]; };
    pc.onicecandidate = e => { if(e.candidate) ws.send(JSON.stringify({type:'ice', candidate:e.candidate})); };

    ws.onmessage = async (evt) => {
      const msg = JSON.parse(evt.data);
      if(msg.type === 'offer'){
        await pc.setRemoteDescription(msg.offer);
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        ws.send(JSON.stringify({type:'answer', answer}));
      } else if(msg.type === 'answer'){
        await pc.setRemoteDescription(msg.answer);
      } else if(msg.type === 'ice'){
        try{ await pc.addIceCandidate(msg.candidate); }catch(e){console.warn(e)}
      }
    };

    // create offer (caller)
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    ws.send(JSON.stringify({type:'offer', offer}));
  };

  start().catch(e=>console.error(e));
})();