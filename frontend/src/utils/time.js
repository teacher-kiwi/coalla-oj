import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'

dayjs.extend(duration)
dayjs.extend(relativeTime)
dayjs.extend(utc)

// 사이트 전체의 날짜 표기는 2026-09-24 14:05 처럼 0 을 채운 꼴 하나로 맞춘다.
// 초는 대부분 쓸모가 없어 빼고, 필요한 화면(채점 목록 등)만 따로 붙인다.
function utcToLocal (utcDt, format = 'YYYY-MM-DD HH:mm') {
  return dayjs.utc(utcDt).local().format(format)
}

// 대회가 얼마나 이어지는지. humanize() 는 영어로 나오고 "2 days" 처럼 뭉뚱그려서
// (1.5일도 2일도 같은 말이 된다) 대회 길이 표기에는 맞지 않아 직접 만든다.
function durationFn (startTime, endTime) {
  const totalMinutes = Math.abs(dayjs(endTime).diff(dayjs(startTime), 'minute'))
  if (totalMinutes < 60) return `${totalMinutes}분`

  const days = Math.floor(totalMinutes / (60 * 24))
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60)
  const minutes = totalMinutes % 60
  const parts = []
  if (days) parts.push(`${days}일`)
  if (hours) parts.push(`${hours}시간`)
  // 하루가 넘어가면 분 단위는 군더더기라 뺀다
  if (minutes && !days) parts.push(`${minutes}분`)
  return parts.join(' ')
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
