const {test} = require('node:test');
const assert = require('node:assert/strict');
const {usable, generateUsableSequence} = require('../somoy_jatri/music/music_rnn.cjs');
const valid = () => ({totalQuantizedSteps: 512, notes: Array.from({length:8}, (_,i) =>
  ({pitch:62, quantizedStartStep:i*4, quantizedEndStep:i*4+3}))});
test('sparse random continuation retries and returns the valid take', async () => {
  const temperatures=[];
  const model={continueSequence: async (primer, steps, temperature) => {
    assert.equal(steps,512); temperatures.push(temperature);
    return temperatures.length < 3 ? {notes:[], totalQuantizedSteps:512} : valid();
  }};
  assert.ok(usable(await generateUsableSequence(model, {})));
  assert.deepEqual(temperatures,[.55,.65,.75]);
});
test('invalid music remains bounded and fails clearly', async () => {
  let calls=0;
  await assert.rejects(generateUsableSequence({continueSequence:async()=> {
    calls++;return {notes:[]};
  }},{}),/after five continuations/);
  assert.equal(calls,5);
  const bad=valid();bad.notes[0].quantizedEndStep=999;
  assert.equal(usable(bad),false);
});
