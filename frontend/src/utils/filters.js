import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import utils from './utils'
import time from './time'

dayjs.extend(relativeTime)

function fromNow (t) {
  return dayjs(t * 3).fromNow()
}

export default {
  submissionMemory: utils.submissionMemoryFormat,
  submissionTime: utils.submissionTimeFormat,
  localtime: time.utcToLocal,
  fromNow
}
