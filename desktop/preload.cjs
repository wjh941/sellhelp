const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld(
  'sellhelp',
  Object.freeze({
    restartBackend: async () => (await ipcRenderer.invoke('sellhelp:restart-backend')) === true,
  }),
)
