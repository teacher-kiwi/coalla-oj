import axios from 'axios'
import { ElMessage } from 'element-plus'
import storage from '@/utils/storage'
import { STORAGE_KEY } from '@/utils/constants'

function submissionMemoryFormat (memory) {
  if (memory === undefined) return '--'
  let t = parseInt(memory) / 1048576
  return String(t.toFixed(0)) + 'MB'
}

function submissionTimeFormat (time) {
  if (time === undefined) return '--'
  return time + 'ms'
}

function getACRate (acCount, totalCount) {
  let rate = totalCount === 0 ? 0.00 : (acCount / totalCount * 100).toFixed(2)
  return String(rate) + '%'
}

function filterEmptyValue (object) {
  let query = {}
  Object.keys(object).forEach(key => {
    if (object[key] || object[key] === 0 || object[key] === false) {
      query[key] = object[key]
    }
  })
  return query
}

function breakLongWords (value, length = 16) {
  let re
  if (escape(value).indexOf('%u') === -1) {
    re = new RegExp('(.{' + length + '})', 'g')
  } else {
    re = new RegExp('(.{' + (length / 2 + 1) + '})', 'g')
  }
  return value.replace(re, '$1\n')
}

function downloadFile (url) {
  return new Promise((resolve, reject) => {
    axios.get(url, { responseType: 'blob' }).then(resp => {
      let headers = resp.headers
      if (headers['content-type'].indexOf('json') !== -1) {
        let fr = new window.FileReader()
        fr.onload = (event) => {
          let data = JSON.parse(event.target.result)
          if (data.error) {
            ElMessage.error(data.data)
          } else {
            ElMessage.error('Invalid file format')
          }
        }
        let b = new window.Blob([resp.data], { type: 'application/json' })
        fr.readAsText(b)
        return
      }
      let link = document.createElement('a')
      link.href = window.URL.createObjectURL(new window.Blob([resp.data], { type: headers['content-type'] }))
      link.download = (headers['content-disposition'] || '').split('filename=')[1]
      document.body.appendChild(link)
      link.click()
      link.remove()
      resolve()
    }).catch(() => {})
  })
}

function getLanguages () {
  return new Promise((resolve, reject) => {
    let languages = storage.get(STORAGE_KEY.languages)
    if (languages) {
      resolve(languages)
      return
    }
    import('@oj/api').then(({ default: ojAPI }) => {
      ojAPI.getLanguages().then(res => {
        let languages = res.data.data.languages
        storage.set(STORAGE_KEY.languages, languages)
        resolve(languages)
      }, err => {
        reject(err)
      })
    })
  })
}

export default {
  submissionMemoryFormat,
  submissionTimeFormat,
  getACRate,
  filterEmptyValue,
  breakLongWords,
  downloadFile,
  getLanguages
}
