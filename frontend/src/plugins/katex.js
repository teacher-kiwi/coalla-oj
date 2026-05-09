import 'katex'
import renderMathInElement from 'katex/contrib/auto-render/auto-render'
import 'katex/dist/katex.min.css'

const defaultOptions = {
  errorCallback: () => {},
  throwOnError: false,
  delimiters: [
    { left: '$$', right: '$$', display: true },
    { left: '$', right: '$', display: false },
    { left: '\\[', right: '\\]', display: true },
    { left: '\\(', right: '\\)', display: false }
  ]
}

function render (el, binding) {
  let options = {}
  if (binding.value) {
    options = binding.value.options || {}
  }
  Object.assign(options, defaultOptions)
  renderMathInElement(el, options)
}

export default {
  install (app) {
    app.directive('katex', {
      mounted: render,
      updated: render
    })
  }
}
