import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as Blockly from 'blockly'
import { pythonGenerator } from 'blockly/python'

// 블록 정의와 생성기를 등록한다(부수 효과 import)
import '@oj/components/blockly/blocks'

// 학생이 조립한 블록이 어떤 파이썬 코드가 되는지 확인한다.
// 여기가 틀리면 학생은 블록을 맞게 놓고도 오답을 받고, 원인을 스스로 찾을 수 없다.

let workspace

beforeEach(() => {
  workspace = new Blockly.Workspace()
  pythonGenerator.init(workspace)
})

afterEach(() => {
  workspace.dispose()
})

/** 값 블록 하나를 만들고 필드를 채운다 */
function makeBlock (type, fields = {}) {
  const block = workspace.newBlock(type)
  for (const [name, value] of Object.entries(fields)) {
    block.setFieldValue(value, name)
  }
  return block
}

/** child 블록을 parent 의 입력에 꽂는다 */
function connect (parent, inputName, child) {
  parent.getInput(inputName).connection.connect(child.outputConnection)
}

/** 값 블록이 만들어내는 코드 문자열 */
function codeOf (block) {
  return pythonGenerator.blockToCode(block)[0]
}

function number (value) {
  return makeBlock('math_number', { NUM: String(value) })
}

function text (value) {
  return makeBlock('text', { TEXT: value })
}

describe('사칙연산 (calc_basic)', () => {
  it('두 수를 연산자로 잇는다', () => {
    const block = makeBlock('calc_basic', { OP: '+' })
    connect(block, 'A', number(1))
    connect(block, 'B', number(2))
    expect(codeOf(block)).toBe('1 + 2')
  })

  it('곱셈 안에 든 덧셈에 괄호가 붙는다', () => {
    // 괄호가 빠지면 (1 + 2) * 3 이 1 + 2 * 3 이 되어 답이 달라진다
    const inner = makeBlock('calc_basic', { OP: '+' })
    connect(inner, 'A', number(1))
    connect(inner, 'B', number(2))

    const outer = makeBlock('calc_basic', { OP: '*' })
    connect(outer, 'A', inner)
    connect(outer, 'B', number(3))

    expect(codeOf(outer)).toBe('(1 + 2) * 3')
  })

  it('입력이 비면 0 으로 채워 문법 오류를 막는다', () => {
    const block = makeBlock('calc_basic', { OP: '-' })
    expect(codeOf(block)).toBe('0 - 0')
  })
})

describe('나눗셈 (calc_division)', () => {
  it('몫과 나머지 연산자를 그대로 쓴다', () => {
    // 드롭다운에는 몫(//)과 나머지(%)뿐이다. 일반 나눗셈은 calc_basic 의 / 를 쓴다.
    for (const op of ['//', '%']) {
      const block = makeBlock('calc_division', { MODE: op })
      connect(block, 'A', number(10))
      connect(block, 'B', number(3))
      expect(codeOf(block), `연산자 ${op}`).toBe(`10 ${op} 3`)
    }
  })

  it('나누는 수가 비면 1 로 채워 0 나눗셈을 피한다', () => {
    const block = makeBlock('calc_division', { MODE: '//' })
    connect(block, 'A', number(10))
    expect(codeOf(block)).toBe('10 // 1')
  })
})

describe('형 변환 (text_to_number)', () => {
  it('int 와 float 를 고른 대로 감싼다', () => {
    const asInt = makeBlock('text_to_number', { TYPE: 'int' })
    connect(asInt, 'TXT', text('10'))
    expect(codeOf(asInt)).toBe("int('10')")

    const asFloat = makeBlock('text_to_number', { TYPE: 'float' })
    connect(asFloat, 'TXT', text('1.5'))
    expect(codeOf(asFloat)).toBe("float('1.5')")
  })
})

describe('입력 (input_readline)', () => {
  it('줄 단위로 읽고 공백을 정리한다', () => {
    const block = makeBlock('input_readline')
    expect(codeOf(block)).toBe('input().strip()')
  })

  it('빠른 입력 정의를 한 번 넣는다', () => {
    const block = makeBlock('input_readline')
    codeOf(block)
    // 채점에서 시간 초과를 피하려고 input 을 바꿔 끼운다
    expect(pythonGenerator.definitions_.fast_io).toBe('input = open(0).readline')
  })
})

describe('문자열 나누기 (text_split)', () => {
  it('구분자를 주면 그대로 넘긴다', () => {
    const block = makeBlock('text_split')
    connect(block, 'TXT', text('a,b'))
    connect(block, 'SEP', text(','))
    expect(codeOf(block)).toBe("'a,b'.split(',')")
  })

  it('구분자가 비면 인자 없이 split 한다 (공백 기준)', () => {
    const block = makeBlock('text_split')
    connect(block, 'TXT', text('a b'))
    expect(codeOf(block)).toBe("'a b'.split()")
  })
})

describe('리스트 통계 (list_stats)', () => {
  it('합·최솟값·최댓값을 파이썬 내장 함수로 바꾼다', () => {
    const cases = { SUM: 'sum', MIN: 'min', MAX: 'max' }
    for (const [field, fn] of Object.entries(cases)) {
      const block = makeBlock('list_stats', { OP: field })
      expect(codeOf(block), field).toBe(`${fn}([])`)
    }
  })
})

describe('리스트 값 숫자로 바꾸기 (list_map_number)', () => {
  it('map 으로 감싼 뒤 list 로 되돌린다', () => {
    const block = makeBlock('list_map_number', { TYPE: 'int' })
    expect(codeOf(block)).toBe('list(map(int, []))')
  })
})

describe('n번 값 꺼내기', () => {
  // 두 블록 모두 툴팁에 "첫 번째는 0번"이라고 안내한다. 즉 학생이 넣은 번호가
  // 그대로 파이썬 인덱스가 되어야 하고, 여기서 1이 더해지거나 빠지면 안 된다.
  it('리스트 번호를 그대로 인덱스로 쓴다', () => {
    const block = makeBlock('list_get_nth')
    connect(block, 'INDEX', number(0))
    expect(codeOf(block)).toBe('[][0]')

    const second = makeBlock('list_get_nth')
    connect(second, 'INDEX', number(1))
    expect(codeOf(second)).toBe('[][1]')
  })

  it('문자열도 같은 규칙을 쓴다', () => {
    const block = makeBlock('text_get_nth')
    connect(block, 'TXT', text('abc'))
    connect(block, 'INDEX', number(0))
    expect(codeOf(block)).toBe("'abc'[0]")
  })
})

describe('등록 상태', () => {
  it('툴박스에 넣은 커스텀 블록이 모두 생성기를 갖는다', () => {
    // 생성기가 없으면 학생 화면에서 코드가 빈 채로 제출된다
    const custom = ['text_to_number', 'calc_basic', 'calc_division', 'list_stats',
      'list_map_number', 'list_get_nth', 'list_append', 'list_pop', 'list_sort',
      'text_split', 'text_get_nth', 'input_readline', 'loop_range', 'loop_each',
      'print_list_spaced', 'list_count', 'variable_assign', 'variable_change',
      'procedure_return', 'procedure_call_value']
    for (const type of custom) {
      expect(Blockly.Blocks[type], `${type} 블록 정의`).toBeDefined()
      expect(pythonGenerator.forBlock[type], `${type} 생성기`).toBeTypeOf('function')
    }
  })
})

describe('변수 이름', () => {
  function codeWithVariable (name) {
    const variable = workspace.getVariableMap().createVariable(name)
    const set = workspace.newBlock('variables_set')
    set.setFieldValue(variable.getId(), 'VAR')
    connect(set, 'VALUE', number(1))
    return pythonGenerator.workspaceToCode(workspace)
  }

  it('한글 이름을 그대로 쓴다', () => {
    // 예전에는 _EC_88_AB... 로 바뀌어 학생이 코드 보기·오류에서 자기 변수를 못 알아봤다
    expect(codeWithVariable('숫자들')).toContain('숫자들 = 1')
  })

  it('파이썬 이름에 못 쓰는 글자는 _ 로 바꾼다', () => {
    expect(codeWithVariable('내 점수!')).toContain('내_점수_ = 1')
  })

  it('숫자로 시작하면 앞에 붙여 문법 오류를 막는다', () => {
    expect(codeWithVariable('1등')).toContain('my_1등 = 1')
  })

  it('파이썬 예약어·내장 함수와 겹치면 피해 간다', () => {
    expect(codeWithVariable('print')).not.toMatch(/^print = 1/m)
  })
})

describe('연산자 표시', () => {
  function labels (type, field) {
    return workspace.newBlock(type).getField(field).getOptions().map(([label]) => label)
  }

  it('블록 옆에 파이썬 연산자를 함께 보여준다', () => {
    expect(labels('calc_basic', 'OP')).toEqual(['+', '-', '× (*)', '÷ (/)'])
    expect(labels('calc_division', 'MODE')).toEqual(['몫 (//)', '나머지 (%)'])
  })
})

/** 변수 값 블록 */
function variable (name) {
  const v = workspace.getVariableMap().getVariable(name) || workspace.getVariableMap().createVariable(name)
  const block = workspace.newBlock('variables_get')
  block.setFieldValue(v.getId(), 'VAR')
  return block
}

/** 문장 블록을 parent 의 DO 안에 넣는다 */
function putInside (parent, child) {
  parent.getInput('DO').connection.connect(child.previousConnection)
}

function printOf (valueBlock) {
  const print = workspace.newBlock('text_print')
  connect(print, 'TEXT', valueBlock)
  return print
}

// 블록이 생기거나 이름이 바뀌었다는 알림은 잠깐 뒤에 한꺼번에 전달된다
const settle = () => new Promise(resolve => setTimeout(resolve, 20))

describe('범위 반복 (loop_range)', () => {
  it('파이썬 range 그대로 끝값은 넣지 않는다', () => {
    const loop = makeBlock('loop_range')
    connect(loop, 'FROM', number(0))
    connect(loop, 'TO', variable('n'))
    putInside(loop, printOf(variable('i')))
    expect(pythonGenerator.blockToCode(loop)).toBe('for i in range(0, n):\n  print(i)\n')
  })

  it('안이 비면 pass 로 채워 문법 오류를 막는다', () => {
    const loop = makeBlock('loop_range')
    connect(loop, 'FROM', number(1))
    connect(loop, 'TO', number(5))
    expect(pythonGenerator.blockToCode(loop)).toBe('for i in range(1, 5):\n  pass\n')
  })

  it('이름 칸에 쓴 이름이 변수로 생겨 변수 칸에서 꺼내 쓸 수 있다', async () => {
    const loop = makeBlock('loop_range')
    await settle()
    expect(workspace.getVariableMap().getVariable('i')).not.toBeNull()

    loop.setFieldValue('번호', 'VAR')
    await settle()
    expect(workspace.getVariableMap().getVariable('번호')).not.toBeNull()
  })

  it('이름을 비우면 받지 않는다', () => {
    const loop = makeBlock('loop_range')
    loop.setFieldValue('   ', 'VAR')
    expect(loop.getFieldValue('VAR')).toBe('i')
  })

  it('변수 칸에서 이름을 바꾸면 반복 블록도 따라 바뀐다', async () => {
    const loop = makeBlock('loop_range')
    await settle()
    const variables = workspace.getVariableMap()
    variables.renameVariable(variables.getVariable('i'), 'k')
    await settle()
    expect(loop.getFieldValue('VAR')).toBe('k')
  })

  it('반복 멈추기 블록을 안에 넣을 수 있다', async () => {
    const { loops } = await import('blockly/blocks')
    expect(loops.loopTypes.has('loop_range')).toBe(true)
    expect(loops.loopTypes.has('loop_each')).toBe(true)
  })
})

describe('각 요소 반복 (loop_each)', () => {
  it('리스트의 값을 하나씩 변수에 넣는다', () => {
    const loop = makeBlock('loop_each')
    connect(loop, 'LIST', variable('점수들'))
    putInside(loop, printOf(variable('값')))
    expect(pythonGenerator.blockToCode(loop)).toBe('for 값 in 점수들:\n  print(값)\n')
  })
})

describe('리스트 띄어서 출력 (print_list_spaced)', () => {
  it('print(*리스트) 로 한 칸씩 띄어 출력한다', () => {
    const block = makeBlock('print_list_spaced')
    connect(block, 'LIST', variable('L'))
    expect(pythonGenerator.blockToCode(block)).toBe('print(*L)\n')
  })

  it('입력을 나눈 리스트를 바로 받을 수 있다', () => {
    const split = makeBlock('text_split')
    connect(split, 'TXT', makeBlock('input_readline'))
    const block = makeBlock('print_list_spaced')
    connect(block, 'LIST', split)
    expect(pythonGenerator.blockToCode(block)).toBe('print(*input().strip().split())\n')
  })
})

describe('n번 값 번호에 변수를 넣을 때', () => {
  it('int() 없이 그대로 쓴다', () => {
    const block = makeBlock('text_get_nth')
    connect(block, 'TXT', variable('a'))
    connect(block, 'INDEX', variable('x'))
    expect(codeOf(block)).toBe('a[x]')

    const list = makeBlock('list_get_nth')
    connect(list, 'LIST', variable('L'))
    connect(list, 'INDEX', variable('i'))
    expect(codeOf(list)).toBe('L[i]')
  })
})

describe('각 요소 반복에 텍스트', () => {
  it('텍스트를 끼우면 한 글자씩 반복한다', () => {
    const loop = makeBlock('loop_each')
    connect(loop, 'LIST', variable('a'))
    connect(loop, 'LIST', makeBlock('input_readline'))
    expect(loop.getInputTargetBlock('LIST').type).toBe('input_readline')
  })
})

describe('값의 개수 (list_count)', () => {
  it('count 로 센다', () => {
    const block = makeBlock('list_count')
    connect(block, 'LIST', variable('a'))
    connect(block, 'ITEM', text('S'))
    expect(codeOf(block)).toBe("a.count('S')")
  })
})

/** 앞 칸(TARGET)과 뒤 칸을 채운 설정·바꾸기 블록 */
function assignBlock (type, target, valueInput, value) {
  const block = makeBlock(type)
  connect(block, 'TARGET', target)
  if (value) connect(block, valueInput, value)
  return block
}

function listItem (listName, index) {
  const block = makeBlock('list_get_nth')
  connect(block, 'LIST', variable(listName))
  connect(block, 'INDEX', index)
  return block
}

describe('설정 (variable_assign)', () => {
  it('변수에 값을 넣는다', () => {
    const block = assignBlock('variable_assign', variable('n'), 'VALUE', number(5))
    expect(pythonGenerator.blockToCode(block)).toBe('n = 5\n')
  })

  it('리스트의 n번 값을 바꾼다', () => {
    const block = assignBlock('variable_assign', listItem('승리', variable('i')), 'VALUE', number(0))
    expect(pythonGenerator.blockToCode(block)).toBe('승리[i] = 0\n')
  })

  it('앞 칸에 바꿀 수 없는 블록을 넣으면 꺼져서 코드에서 빠진다', async () => {
    // 숫자 = 값 은 문법 오류, 문자열 글자 바꾸기는 실행 오류다
    for (const bad of [number(3), makeBlock('text_get_nth')]) {
      const block = assignBlock('variable_assign', bad, 'VALUE', number(1))
      await settle()
      expect(block.isEnabled()).toBe(false)
      expect(pythonGenerator.workspaceToCode(workspace)).not.toContain('= 1')
      block.dispose()
    }
  })

  it('고쳐 넣으면 다시 켜진다', async () => {
    const block = assignBlock('variable_assign', number(3), 'VALUE', number(1))
    await settle()
    expect(block.isEnabled()).toBe(false)
    block.getInputTargetBlock('TARGET').dispose()
    connect(block, 'TARGET', variable('n'))
    await settle()
    expect(block.isEnabled()).toBe(true)
  })

  it('앞 칸이 비면 아무 코드도 만들지 않는다', () => {
    const block = makeBlock('variable_assign')
    expect(pythonGenerator.blockToCode(block)).toBe('')
  })
})

describe('바꾸기 (variable_change)', () => {
  it('+= 한 줄로 만든다', () => {
    const block = assignBlock('variable_change', variable('점수'), 'DELTA', number(1))
    expect(pythonGenerator.blockToCode(block)).toBe('점수 += 1\n')
  })

  it('리스트의 값도 바꿀 수 있다', () => {
    const block = assignBlock('variable_change', listItem('승리', number(2)), 'DELTA', number(-1))
    expect(pythonGenerator.blockToCode(block)).toBe('승리[2] += -1\n')
  })

  it('예전 바꾸기 블록도 같은 코드가 되고 import 가 붙지 않는다', () => {
    const v = workspace.getVariableMap().createVariable('x')
    const block = workspace.newBlock('math_change')
    block.setFieldValue(v.getId(), 'VAR')
    connect(block, 'DELTA', number(1))
    const code = pythonGenerator.workspaceToCode(workspace)
    expect(code).toContain('x += 1')
    expect(code).not.toContain('isinstance')
    expect(code).not.toContain('import')
  })
})

/** 함수 만들기 블록 (이름만) */
function defineFunction (name) {
  const def = workspace.newBlock('procedures_defnoreturn')
  def.setFieldValue(name, 'NAME')
  return def
}

describe('함수 돌려줌 (procedure_return)', () => {
  it('함수 안의 만약 블록 안에서 값을 돌려준다', async () => {
    const def = defineFunction('판정')
    const ifBlock = workspace.newBlock('controls_if')
    connect(ifBlock, 'IF0', makeBlock('logic_boolean', { BOOL: 'TRUE' }))
    def.getInput('STACK').connection.connect(ifBlock.previousConnection)
    const ret = makeBlock('procedure_return')
    connect(ret, 'VALUE', number(1))
    ifBlock.getInput('DO0').connection.connect(ret.previousConnection)
    await settle()
    expect(ret.isEnabled()).toBe(true)
    expect(pythonGenerator.workspaceToCode(workspace)).toContain('  if True:\n    return 1\n')
  })

  it('값 칸이 비면 return 만 쓴다', () => {
    expect(pythonGenerator.blockToCode(makeBlock('procedure_return'))).toBe('return\n')
  })

  it('함수 밖에 두면 꺼진다', async () => {
    const ret = makeBlock('procedure_return')
    await settle()
    expect(ret.isEnabled()).toBe(false)
    expect(pythonGenerator.workspaceToCode(workspace)).not.toContain('return')
  })

  it('함수 만들기 블록에 설명 메모가 붙지 않는다', async () => {
    await import('@oj/components/blockly/setup')
    const def = defineFunction('f')
    expect(def.getCommentText()).toBeNull()
  })
})

describe('함수를 값으로 쓰기 (procedure_call_value)', () => {
  it('함수 만들기 블록과 짝이 되어 같은 이름 함수를 새로 만들지 않는다', async () => {
    const def = defineFunction('판정')
    const ret = makeBlock('procedure_return')
    connect(ret, 'VALUE', number(1))
    def.getInput('STACK').connection.connect(ret.previousConnection)
    const call = Blockly.serialization.blocks.append(
      { type: 'procedure_call_value', extraState: { name: '판정', params: [] } }, workspace)
    const set = assignBlock('variable_assign', variable('res'), 'VALUE', call)
    await settle()

    const defs = workspace.getAllBlocks(false).filter(b => b.type.startsWith('procedures_def'))
    expect(defs).toHaveLength(1)
    expect(call.isEnabled()).toBe(true)
    expect(pythonGenerator.blockToCode(set)).toBe('res = 판정()\n')
  })

  it('함수 이름을 바꾸면 값 블록도 따라 바뀐다', async () => {
    const def = defineFunction('f')
    const call = Blockly.serialization.blocks.append(
      { type: 'procedure_call_value', extraState: { name: 'f', params: [] } }, workspace)
    await settle()
    def.setFieldValue('g', 'NAME')
    expect(call.getProcedureCall()).toBe('g')
  })
})

describe('도구 상자 목록', () => {
  it('변수 칸: 설정·바꾸기 블록 앞 칸에 최근 변수가 끼워져 나온다', async () => {
    const { variableFlyoutBlocks } = await import('@oj/components/blockly/toolbox/ioCategory')
    expect(variableFlyoutBlocks(workspace)).toEqual([])
    workspace.getVariableMap().createVariable('a')
    workspace.getVariableMap().createVariable('b')
    const items = variableFlyoutBlocks(workspace)
    expect(items.map(i => i.type)).toEqual(['variable_assign', 'variable_change', 'variables_get', 'variables_get'])
    // 실제로 만들어 보면 b 변수가 끼워진 설정 블록이 된다
    const block = Blockly.serialization.blocks.append(items[0], workspace)
    expect(pythonGenerator.blockToCode(block)).toBe('b = 0\n')
  })

  it('함수 칸: 함수마다 실행 블록과 값 블록을 둘 다 준다', async () => {
    const { procedureFlyout } = await import('@oj/components/blockly/toolbox/procedureCategory')
    defineFunction('판정')
    const types = procedureFlyout(workspace).map(i => i.type)
    expect(types).toEqual(['procedures_defnoreturn', 'procedure_return',
      'procedures_callnoreturn', 'procedure_call_value'])
  })
})
