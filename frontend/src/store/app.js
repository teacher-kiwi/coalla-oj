import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    website: {},
    // 모달은 로그인 하나뿐이라 열림 여부만 둔다
    modalStatus: {
      visible: false
    }
  }),
  actions: {
    async getWebsiteConfig () {
      const { default: api } = await import('@oj/api')
      const res = await api.getWebsiteConf()
      this.website = res.data.data
    },
    changeModalStatus ({ visible }) {
      if (visible !== undefined) this.modalStatus.visible = visible
    },
    changeDomTitle (title) {
      if (title) {
        document.title = this.website.website_name_shortcut + ' | ' + title
      }
    }
  }
})
