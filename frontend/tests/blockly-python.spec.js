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
      'text_split', 'text_get_nth', 'input_readline']
    for (const type of custom) {
      expect(Blockly.Blocks[type], `${type} 블록 정의`).toBeDefined()
      expect(pythonGenerator.forBlock[type], `${type} 생성기`).toBeTypeOf('function')
    }
  })
})
