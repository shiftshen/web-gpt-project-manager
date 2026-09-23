/** Visible Ego Lite ChatGPT bridge. The caller supplies a managed task-space page. */
import { readFile } from 'node:fs/promises'

const args = globalThis.PM_EGO_ARGS || {}
const task = await globalThis.taskSpace(args.space)
const page = task.page(args.page)
if (!page) throw new Error('Ego page missing')

const stateCode = `(()=>{const buttons=[...document.querySelectorAll('button')];const editor=document.querySelector('#prompt-textarea');return JSON.stringify({url:location.href,title:document.title,busy:buttons.some(e=>/^(停止回答|停止生成|Stop generating|Stop response)$/i.test(e.getAttribute('aria-label')||'')||e.dataset.testid==='stop-button'),draft:editor?(editor.innerText||editor.value||''):'',hasEditor:!!editor,configurationControls:buttons.filter(e=>e.getClientRects().length&&!e.closest('nav,aside')&&/model|模型|GPT|Work|工作|推理|thinking/i.test((e.getAttribute('aria-label')||'')+' '+e.innerText)).slice(0,12).map(e=>({text:e.innerText.slice(0,100),aria:e.getAttribute('aria-label')}))});})()`
async function evaluate(code) {
  const value = await page.evaluate(source => eval(source), code)
  return typeof value === 'string' ? JSON.parse(value) : value
}
function checkOrigin(state) {
  if (!state.url.startsWith('https://chatgpt.com/')) throw new Error('Wrong origin')
}

if (args.action === 'read') {
  const state = await evaluate(args.code || stateCode)
  if (args.code === undefined) checkOrigin(state)
  console.log(JSON.stringify(state))
} else if (args.action === 'send') {
  const prompt = await readFile(args.prompt, 'utf8')
  const before = await evaluate(stateCode)
  checkOrigin(before)
  if (args.expectedUrl && before.url !== args.expectedUrl) throw new Error('Wrong project-manager URL')
  if (before.busy) throw new Error('Manager still responding')
  const roundVisible = await evaluate(`JSON.stringify([...document.querySelectorAll('[data-message-author-role="user"]')].some(e=>e.innerText.includes(${JSON.stringify(args.roundId)})))`)
  if (roundVisible) throw new Error('Round already visible; do not resend')
  if (before.draft.trim()) throw new Error('Existing draft; refusing overwrite')
  if (!before.hasEditor) throw new Error('No composer')
  await page.fill('#prompt-textarea', prompt)
  const draft = await evaluate(stateCode)
  if (draft.draft.trim() !== prompt.trim()) throw new Error('Composer text mismatch; inspect before retry')
  await page.click('loc=css:button[data-testid="send-button"],button[aria-label="发送提示词"],button[aria-label="发送消息"],button[aria-label="Send prompt"],button[aria-label="Send message"]', { label: 'send manager review prompt' })
  await page.waitForFunction(roundId => [...document.querySelectorAll('[data-message-author-role="user"]')].some(e => e.innerText.includes(roundId)), args.roundId, { timeout: 12000 })
  const after = await evaluate(stateCode)
  console.log(JSON.stringify({ status: 'submitted', url: after.url, busy: after.busy }))
} else {
  throw new Error('Unknown Ego action')
}
