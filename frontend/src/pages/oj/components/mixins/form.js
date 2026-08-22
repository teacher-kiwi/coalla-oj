import { ElMessage } from 'element-plus'

export function useForm () {
  function validateForm (formRef) {
    return new Promise((resolve) => {
      if (!formRef) {
        resolve(false)
        return
      }
      formRef.validate((valid) => {
        if (!valid) {
          ElMessage.error('입력값을 확인해주세요')
          resolve(false)
        } else {
          resolve(true)
        }
      })
    })
  }

  return { validateForm }
}
