(function(){
  const doc = new Y.Doc();
  const wsHost = (location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.hostname + ':1234';
  const provider = new window.YWebsocket.WebsocketProvider(wsHost, 'jarvis-doc', doc);
  const ytext = doc.getText('shared-text');
  const textarea = document.getElementById('editor');

  // apply local changes to Yjs
  textarea.addEventListener('input', () => {
    // replace entire text (simple approach)
    doc.transact(() => {
      ytext.delete(0, ytext.length)
      ytext.insert(0, textarea.value)
    })
  })

  // observe remote changes and update textarea
  ytext.observe(event => {
    const val = ytext.toString();
    if (textarea.value !== val) textarea.value = val;
  })

  // initialize textarea with current content
  textarea.value = ytext.toString();

  provider.on('status', e => console.log('Yjs status:', e.status));
})();
