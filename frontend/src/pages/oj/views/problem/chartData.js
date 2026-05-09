const pieColorMap = {
  'AC': '#19be6b',
  'WA': '#ed3f14',
  'TLE': '#ff9300',
  'MLE': '#f7de00',
  'RE': '#ff6104',
  'CE': '#80848f',
  'PAC': '#2d8cf0'
}

function getItemColor (obj) {
  return pieColorMap[obj.name]
}

const pie = {
  legend: {
    left: 'center',
    top: '10',
    orient: 'horizontal',
    data: ['AC', 'WA']
  },
  series: [
    {
      name: 'Summary',
      type: 'pie',
      radius: '80%',
      center: ['50%', '55%'],
      itemStyle: {
        color: getItemColor
      },
      data: [
        {value: 0, name: 'WA'},
        {value: 0, name: 'AC'}
      ],
      label: {
        position: 'inner',
        show: true,
        formatter: '{b}: {c}\n {d}%',
        fontWeight: 'bold'
      }
    }
  ]
}

const largePie = {
  legend: {
    left: 'center',
    top: '10',
    orient: 'horizontal',
    itemGap: 20,
    data: ['AC', 'RE', 'WA', 'TLE', 'PAC', 'MLE']
  },
  series: [
    {
      name: 'Detail',
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '55%'],
      itemStyle: {
        color: getItemColor
      },
      data: [
        {value: 0, name: 'RE'},
        {value: 0, name: 'WA'},
        {value: 0, name: 'TLE'},
        {value: 0, name: 'AC'},
        {value: 0, name: 'MLE'},
        {value: 0, name: 'PAC'}
      ],
      label: {
        formatter: '{b}: {c}\n {d}%'
      },
      labelLine: {}
    },
    {
      name: 'Summary',
      type: 'pie',
      radius: '30%',
      center: ['50%', '55%'],
      itemStyle: {
        color: getItemColor
      },
      data: [
        {value: '0', name: 'WA'},
        {value: 0, name: 'AC', selected: true}
      ],
      label: {
        position: 'inner',
        formatter: '{b}: {c}\n {d}%'
      }
    }
  ]
}

export { pie, largePie }
