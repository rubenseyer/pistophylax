Pistophylax
======
 > **πιστο-φύλαξ** [ῠ], ᾰκος, ὁ, ἡ, _guardian of truth_, Orph.H.8.17.
 >(Lidell & Scott's _Greek-English Lexicon_, 9th ed.)

_Pistophylax_ is an assistant for natural deduction proofs in propositional logic.
No axiomatic system is imposed on the user; you may specify any rules you like (even inconsistent systems!).

To introduce the syntax, an example proof of [Modus tollens](https://en.wikipedia.org/wiki/Modus_tollens):
```
prove MT. P → Q, ¬Q ⊢ ¬P
  P → Q : premise
  ¬Q : premise
  assume
    P : assumption
    Q : →e 1 ..
    ⊥ : ¬e 2 ..
  end
  ¬P : ¬i [..]
qed
```
Of course, this makes no sense without specifying the rules and axioms used.
[An example set of axioms](./tests/axioms.ve) is provided, in which this rule is proved in context.

The best way to understand the syntax in detail is to look at the example axioms and
[the grammar definition](pistophylax/grammar.lark).
In addition, [a great number of test proofs](./tests) from Huth, M. and Ryan, M., 2004. _Logic in Computer Science_
are available which demonstrates a freer style of the language (and the syntatic sugar shortcuts).

Contributing
------------
This project is licensed under the [GPLv3](./LICENSE).
Contributions welcome!

Future ideas:
 * predicate logic
 * LaTeX output of proofs (flag)
 * ...

