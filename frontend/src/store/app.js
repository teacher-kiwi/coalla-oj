import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    website: {},
    modalStatus: {
      mode: 'login',
      visible: false
    }
  }),
  actions: {
    async getWebsiteConfig () {
      const { default: api } = await import('@oj/api')
      const res = await api.getWebsiteConf()
      this.website = res.data.data
    },
    changeModalStatus ({ mode, visible }) {
      if (mode !== undefined) this.modalStatus.mode = mode
      if (visible !== undefined) this.modalStatus.visible = visible
    },
    changeDomTitle (title) {
      if (title) {
        document.title = this.website.website_name_shortcut + ' | ' + title
      }
    }
  }
})
