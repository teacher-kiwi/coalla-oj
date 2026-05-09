import { ref, h } from 'vue'
import { ElIcon } from 'element-plus'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import utils from '@/utils/utils'

export function useProblem () {
  const statusColumn = ref(false)

  function getACRate (ACCount, TotalCount) {
    return utils.getACRate(ACCount, TotalCount)
  }

  function addStatusColumn (tableColumns, dataProblems) {
    if (statusColumn.value) return
    const needAdd = dataProblems.some((item) => {
      return item.my_status !== null && item.my_status !== undefined
    })
    if (!needAdd) return

    tableColumns.splice(0, 0, {
      width: 60,
      title: ' ',
      render: ({ row }) => {
        const status = row.my_status
        if (status === null || status === undefined) return null
        return h(
          ElIcon,
          { style: { color: status === 0 ? '#19be6b' : '#ed3f14', fontSize: '16px' } },
          () => h(status === 0 ? CircleCheck : CircleClose)
        )
      }
    })
    statusColumn.value = true
  }

  return { statusColumn, getACRate, addStatusColumn }
}
