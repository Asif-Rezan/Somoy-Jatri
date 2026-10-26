// Free CPU inference using Magenta's pretrained 13 MB MelodyRNN.
const fs = require('fs');

async function main() {
  const tf = require('@tensorflow/tfjs');
  const {MusicRNN} = require('@magenta/music/node/music_rnn');
  await tf.setBackend('cpu');
  await tf.ready();
  const model = new MusicRNN('https://storage.googleapis.com/magentadata/js/checkpoints/music_rnn/basic_rnn');
  await model.initialize();
  // Newly composed seed phrase, not a borrowed song.
  // An original D-Dorian motif: mysterious, with a brighter natural sixth.
  const pitches = [62, 64, 65, 69, 71, 69, 67, 64];
  const primer = {quantizationInfo: {stepsPerQuarter: 4}, totalQuantizedSteps: 32,
    notes: pitches.map((pitch, i) => ({pitch, quantizedStartStep: i * 4, quantizedEndStep: i * 4 + 3}))};
  try {
    const result = await generateUsableSequence(model, primer);
    const output = process.argv[2] || 'music-notes.json';
    fs.writeFileSync(output + '.tmp', JSON.stringify(result));
    fs.renameSync(output + '.tmp', output);
    console.log(JSON.stringify({check: 'Free CPU MusicRNN', passed: true, notes: result.notes.length}));
  } finally {
    model.dispose();
  }
}

function usable(sequence) {
  return sequence && sequence.totalQuantizedSteps === 512 &&
    Array.isArray(sequence.notes) && sequence.notes.length >= 8 &&
    sequence.notes.every(n => Number.isInteger(n.pitch) && n.pitch >= 0 && n.pitch <= 127 &&
      Number.isInteger(n.quantizedStartStep) && Number.isInteger(n.quantizedEndStep) &&
      n.quantizedStartStep >= 0 && n.quantizedEndStep > n.quantizedStartStep &&
      n.quantizedEndStep <= 512);
}

async function generateUsableSequence(model, primer) {
  // A stochastic continuation can be nearly all rests. Retry independent takes
  // with a little more variety; never publish silence or substitute a repeated loop.
  for (const temperature of [0.55, 0.65, 0.75, 0.85, 0.95]) {
    const sequence = await model.continueSequence(primer, 512, temperature);
    if (usable(sequence)) return sequence;
    console.log(JSON.stringify({check: 'MusicRNN continuation rejected', temperature}));
  }
  throw new Error('Model generated insufficient music after five continuations');
}

module.exports = {usable, generateUsableSequence};
if (require.main === module) main().catch(error => {console.error(error); process.exit(1);});
