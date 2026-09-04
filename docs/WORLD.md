# The world of the museum

**Status: proposal, September 2026.** Everything in this document is offered for the
owner's approval and is not yet built. The ARCHITECTURE for it is settled and is not a
proposal: the world is data, authored once, read by the labels, the models and the
puzzles (ADR-10). What is proposed here is the CONTENT: five civilizations, a way of
counting, a way of writing, and a bestiary. Rename any of it, replace any of it. The
data files follow whatever this document ends up saying.

The brief it answers: our own historical civilizations and animals, inspired by real
Earth history, eerily similar and not quite it, in the way Riven had its own culture,
history, numbers, writing, animals and ecosystem.

---

## 1. The rule that makes it uncanny

**Every invented thing pairs with a real referent and differs by exactly one structural
fact, and that fact is always a count.**

One difference is uncanny. Two is fantasy, and fantasy is not frightening: a visitor who
sees a six legged horse knows immediately they are somewhere else, and stops looking.
A visitor who sees a hall of memorial figures standing in groups of six, and cannot say
why it feels wrong, is still looking. That is the whole game.

The count is always **six**, and it is the same six everywhere: six figures to a memorial
group, six pieces to an altar set, six eyes on the arthropod, six teeth in the front of
the great predator's jaw, six marks to a written glyph. A player is not told this. They
are shown it about forty times, and then a lock asks them for a number.

**The direction is always the same, too.** Where Earth's version has five, ours has six;
where Earth's has two, ours has six. The world counts in sixes because it counts the
gaps between the fingers rather than the fingers, and one culture in the museum still
says so on a label, once, in a room most players will not visit first.

## 2. How the world counts

**Proposal: base six, written as marks on a stem.**

A digit is a vertical stem carrying nought to five marks. A second stem to its right is
the sixes place, so two stems write every value from nought to thirty five, which is
exactly the range a museum label needs: a count of objects, a depth in strata, a
regnal year. Three stems reach two hundred and fifteen and are used for dates.

```
  |     |.    |..   |...  |.... |.....   |.|
  0     1     2     3     4     5        6

  The seventh value is one mark in the sixes place and none in the units.
```

Why it is worth having at all, rather than printing Arabic numerals on the labels:

- **It is a puzzle mechanic before it is flavour.** The Combination kind (ADR-5) reads
  the numeral table directly, so a dial face, a carat weight on a gem label and the
  answer to a lock are the same data. A player who has learned to read the museum can
  read the lock, and nothing ever teaches them in words.
- **It is learnable without a tutorial**, because the museum repeats it. Riven's
  achievement was that the numbers were discoverable from the world's own furniture.
- **It is checkable.** `tools/verify_world.py` fails if a room's authored count of
  anything contradicts the base.

## 3. How the world writes

**Proposal: the script and the numerals are the same instrument.**

A written glyph is a stem with marks, exactly like a digit, but the marks sit at three
heights instead of one, which gives enough letterforms for a real alphabet while keeping
the family resemblance. Text runs in vertical columns, read top to bottom, columns right
to left. So a label, an inscription on a bronze and a number on a dial all look like
they came from the same hand, and a player who learns to count has already learned half
of how to read.

The museum's own labels are set in the aliens' idea of a museum typeface: our script,
laid out like a modern object label, which is precisely the wrong thing to do to it. The
mismatch is the joke the whole game is built on and it costs nothing to make.

**The lexicon is a file.** Every word the world contains lives in `data/world/lexicon.json`
with its gloss, and `tools/gen_labels.py` writes the labels from it. Nobody types a
label. See ADR-10 for why: a hand typed label is how the museum ends up contradicting
itself in a game about noticing contradictions.

## 4. The five halls, and who made what

Each hall answers one of the photographs in [`reference/README.md`](reference/README.md).
The photograph says what the case looks like and how it is lit. The culture below is what
is actually in it.

### 4.1 The Sethu of the ash delta

*Answers photographs 1, 2 and 3: the men's house, the display house of memorials, the
ancestor post and the whirling slats.*

A river delta people living on a floodplain that a volcanic range renews every few
generations, so their history is measured in ash layers and their architecture is built
to be rebuilt. They carve: ancestor posts stacked with faces, memorial figures with
paired crests, masks with concentric eyes.

**Their one difference:** a memorial group is always six figures, one of which is
carved blank. The blank is not an unfinished figure. It is the ancestor whose name the
group has agreed to stop saying, and every group has one. A visitor counts six figures,
notices one has no face, and is looking at a deliberate act of forgetting.

**What they give the game:** the sequence and resonance puzzles. The debating stool is
struck to make a point; the whirling slats are swung to give the dead a voice, and the
pitch a slat makes is a function of its incised pattern, which means a player can read
a slat and predict its note.

### 4.2 The Vann foundries

*Answers photograph 6: the bronze altar set.*

A dynastic, bureaucratic, metal casting civilization, the one that invented the numerals
everything else in the museum is labelled with. They cast in sets, they number
everything, and their bronzes carry their own inventory marks, which is how the numerals
survived them.

**Their one difference:** an altar set is six pieces, and the sixth is a vessel with no
opening. It was cast sealed, it was never meant to be filled, and it is the piece the
aliens have put in the wrong place because a set of six arranged by size is not the
order the ritual used.

**What they give the game:** the arrangement puzzles, and the museum's only reliable
source of numbers. If a player ever needs to check what a numeral means, a Vann bronze
has it stamped on the base.

### 4.3 The Meridian Concession

*Answers photograph 7: the plantation diorama.*

The invented world's industrial episode: a chartered company that took the delta's
uplands for a crop, worked them with people who did not choose to be there, and left
behind the drying yards, the ledgers and the boundary walls that the diorama models.
This is the hall where the museum's polite label voice is most obviously lying, because
a diorama of a working estate is a picture with the coercion painted out.

**Their one difference:** the ledgers count in sixes like everyone else, and the columns
do not add up. Somebody was falsifying them, and a player who learns the numerals well
enough can find out who.

**A note on handling.** The real diorama photographs a real history of forced labour.
The invented version does not soften that and does not use it as set dressing: the
puzzle is the ledger, and the ledger is evidence. If the owner would rather this hall
carried a different subject, it is the one in this document I would expect to change,
and it should change now rather than after it is built.

### 4.4 Deep time: the Kellish strata

*Answers photographs 4 and 5: the great predator's skull and the trilobite table.*

Not a civilization. The fossil record of the world itself, named for the cliff section
where it was first read. Two animals carry the hall:

- **The vess**, the small armoured arthropod of the shallow seas, forty species of it
  on one backlit table. **Its one difference: six eyes**, in two arcs of three, and only
  some species have them at all, which the hall's heading quietly points at.
- **The kellish predator**, the museum's centrepiece skull. **Its one difference: six
  teeth in the front of the jaw** where Earth's largest predators carry four, and the
  loose teeth in the rack in front of the case are exactly those six.

**What they give the game:** the illumination and combination puzzles, and the strongest
single link between the world and its mechanics, since the skull's six sockets and the
world's base are the same six.

### 4.5 The mineral hall

*Answers photograph 8: the emerald case.*

The hall that is closest to Earth, on purpose. Crystals obey physics, and physics is not
invented, so a beryl is a beryl. What is invented is the provenance: the localities on
the labels are the world's own places, and the cut stones were cut by the Vann, which is
why they are cut in sixes.

**What it gives the game:** the darkest room, the most volumetric light, and a torch
that projects a pattern through a large crystal onto the wall.

### 4.6 The Elmorians, Hall Six (approved, and the first hall built)

*Not from a photograph: from the owner's brief of 2026-09-04, and the first exhibit
prototyped, at `mockups/elmorian-exhibit/`.*

A civilization that was not human, on a world that was. Green skinned, three eyes of
three sizes (the day eye for the near, the middle for the far, and the smallest, high
in the brow, for what stands behind), a single tentacle from the crown called the sil,
no nose and no mouth. They fed by standing in light, which is why they were green and
why their houses were cut into the sunrise face of an escarpment. They spoke by touch,
sil to sil, so every conversation was private and every crowd was silent; their
writing was the same language cut into stone and read by drawing the sil across it.
They went to stone when they died.

**Their one difference is the count itself.** One Elmorian sees three; two Elmorians
facing each other see six, and nothing was counted by fewer eyes than that. The world's
base six numerals are theirs, and "never count alone" is their superstition, which is
why a museum whose halls are almost empty is a museum an Elmorian would not enter.

**What they give the game:** all four puzzle kinds in one hall, on the turning path of
four rooms an Elmorian house was built to: turn the three eyes to the door (the gaze),
stack the light rings under the sun (the light stack), press the greeting into the
pads (the speech), and then re-set all three to what the ancestor chamber's relief
shows (the sixfold gaze). The greeting is light, eye, touch, door; the farewell is
stone, dark, touch, eye, and the farewell is not the greeting reversed.

Every word the hall says is in `mockups/elmorian-exhibit/lore.js` in the museum's
label voice, and the exhibit's own architecture (rooms, doors, fixtures, where the
lights point) is `data/layout/elmorian.json`.

## 5. What is architecture and what is a proposal

**Architecture, settled, in ADR-10:** the world is data in `data/world/`; labels are
generated from it and never typed; the numeral table is read by the puzzle evaluator
rather than copied into it; `tools/verify_world.py` fails the build on a contradiction.
None of that changes if every name below it changes.

**Approved (2026-09-04):** the whole document, and with it the base six, the marks on a
stem, the columns, and the five halls as proposed. The Elmorians were added the same day
and built first. What remains open is only the names, which the owner may still change
one at a time.

The fastest way to review it is to say which of the five halls is right and which is
wrong. Names are cheap to change and structure is not, so the structural claims worth
arguing with are: one count everywhere, one difference per thing, and the numerals doing
double duty as the script.
