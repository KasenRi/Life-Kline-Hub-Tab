import { createApp } from 'vue'
import Newtab from './Newtab.vue'
import { setupApp } from '~/logic/common-setup'
import '../styles'

const app = createApp(Newtab)
setupApp(app)
app.mount('#app')
