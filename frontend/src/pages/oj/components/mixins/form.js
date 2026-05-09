import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@oj/api'

export function useForm () {
  const captchaSrc = ref('')

  function validateForm (formRef) {
    return new Promise((resolve) => {
      if (!formRef) {
        resolve(false)
        return
      }
      formRef.validate((valid) => {
        if (!valid) {
          ElMessage.error('please validate the error fields')
          resolve(false)
        } else {
          resolve(true)
        }
      })
    })
  }

  function getCaptchaSrc () {
    api.getCaptcha().then((res) => {
      captchaSrc.value = res.data.data
    })
  }

  return { captchaSrc, validateForm, getCaptchaSrc }
}
