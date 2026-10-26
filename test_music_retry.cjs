const {test}=require('node:test');
const assert=require('node:assert/strict');
const {usable,generateUsableSequence}=require('./music_rnn.cjs');
const valid={totalQuantizedSteps:256,notes:Array.from({length:8},(_,i)=>({pitch:62,quantizedStartStep:i*4,quantizedEndStep:i*4+3}))};
test('sparse continuation retries without silence fallback',async()=>{
  let calls=0;
  const model={continueSequence:async()=>++calls<3?{notes:[]}:valid};
  assert.equal(await generateUsableSequence(model,{}),valid);
  assert.equal(calls,3);
});
test('invalid music has a bounded failure',async()=>{
  let calls=0;
  await assert.rejects(generateUsableSequence({continueSequence:async()=>{calls++;return {notes:[]};}},{}),/five continuations/);
  assert.equal(calls,5);
  assert.equal(usable({...valid,notes:[{pitch:200}]}),false);
});
