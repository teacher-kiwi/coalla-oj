import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'

dayjs.extend(duration)
dayjs.extend(relativeTime)
dayjs.extend(utc)

function utcToLocal (utcDt, format = 'YYYY-M-D  HH:mm:ss') {
  return dayjs.utc(utcDt).local().format(format)
}

function durationFn (startTime, endTime) {
  let start = dayjs(startTime)
  let end = dayjs(endTime)
  let dur = dayjs.duration(start.diff(end, 'seconds'), 'seconds')
  if (Math.abs(dur.asDays()) >= 1) {
    return dur.humanize()
  }
  return Math.abs(dur.asHours().toFixed(1)) + ' hours'
}

function secondFormat (seconds) {
  let dur = dayjs.duration(seconds, 'seconds')
  return Math.floor(dur.asHours()) + ':' + dur.minutes() + ':' + dur.seconds()
}

export default {
  utcToLocal,
  duration: durationFn,
  secondFormat
}
