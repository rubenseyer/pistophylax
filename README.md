Pistophylax
======
 > **πιστο-φύλαξ** [ῠ], ᾰκος, ὁ, ἡ, _guardian of truth_, Orph.H.8.17.
 >(Lidell & Scott's _Greek-English Lexicon_, 9th ed.)

_Pistophylax_ is an assistant for natural deduction proofs in propositional and predicate logic.
No axiomatic system is imposed on the user; you may specify any rules you like (even inconsistent systems!).

To showcase the syntax, an example proof of [Modus tollens](https://en.wikipedia.org/wiki/Modus_tollens):
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
[An example set of axioms](tests/axioms.px) is provided, in which this rule is proved in context.
For predicate logic, [an extended set of axioms](tests/axioms_predicate.px) are required.

The best way to understand the syntax in detail is to look at the example axioms and
[the grammar definition](pistophylax/grammar.lark).
In addition, [a great number of test proofs](./tests) from Huth, M. and Ryan, M., 2004. _Logic in Computer Science_
are available which demonstrates a freer style of the language (and the syntatic sugar shortcuts).

[A cool, "real" example](./tests/ex_trbisectors.px) is the proof that the bisectors of the sides of a triangle meet at a point (given that a point is on a bisector iff it is equidistant from the endpoints of the corresponding side).

Learn
-----
Every axiom and completed proof defines a rule in the system.
The essence of natural deduction is expressing the reasoning through the application of one rule in each deductive step.
Consider, as an example, the rule [Modus ponens](https://en.wikipedia.org/wiki/Modus_ponens) (or in modern parlance implication elimination), which is stated as
```
axiom →e. P → Q, P ⊢ Q
```
The keyword `axiom` tells us this rule is accepted without proof, as a part of our system.
This rule says that given that some formula P implies another formula Q, and that P is known, we may conclude Q.

Axioms are special in that they may, among other things, take subproofs as arguments (while proofs are only allowed formulas).
For example, the implication introduction axiom is stated as
```
axiom →i. [P Q] ⊢ P → Q
```
This rule says that given that we assuming P can prove Q, we may conclude that P implies Q.
Familiarize yourself with the rest of [the axioms](tests/axioms.px).

We may now attempt our first proof.
Let us prove, as an easy first target, that if P implies Q, and Q implies R, then clearly P implies R.
This proof, of the transitivity of implication or the _hypothetical syllogism_, can be stated as
```
proof →tra. P → Q, Q → R ⊢ P → R
    P → Q : premise
    Q → R : premise
    assume
        P : assumption
        Q : →e 1 ..
        R : →e 2 ..
    end
    P → R : →i [..]
qed
```
A proof must start with `proof`, followed optionally by a name, then `.`, and finally the sequent that is to be proved.
It always ends with `qed`.
Every line of a proof is a formula, followed by a `:`, and then a justification for the line based on the earlier lines.
Some lines are trivially justified, such as the first ones which are just a `premise` (or `pr` for short) given from the start.

Later justifications refer to a rule and then the lines which make up the premises for that particular rule.
Relative references are supported for the last line (`..`) and second-to-last line (`...`).
For example, our first usage of `→e` refers to proof line 1, which is `P → Q`, and the previous line, which is `P`, which both are of the form required of the rule, and so we may conclude `Q`.
We automatically infer the form of the conclusion from parse trees of the premises; in this case, P and Q are both propositional atoms, but from the perspective of `→e` they could just as well be arbitrary formulas.

In this proof, we also have a subproof delimited by `assume` and `end`.
The subproof allows us to introduce a single `assumption` (or `as` for short), with the caveat that the subproof becomes a closure for the inner proof lines.
Thus we cannot refer to these lines from outside.
However, we can refer to the subproof as a whole using square brackets: our application of `→i` refers to `[..]`, the last subproof completed.
The subproof concludes, assuming `P`, that `R` holds, and so we may apply the rule and conclude `P → R`.
With this line, we finish our proof as a whole.
Note that the `Q` in the axiom here was instantiated as `R` in our proof.

A few additional features that have not been explained:
If you need an absolute reference, but want to avoid counting the lines, you can tag any proof line or subproof using `@` to help long proofs.
You are also allowed to, as a special rule, to `copy` any previous proof line in scope, which may be useful to conclude subproofs on the correct conclusion.

### Predicate logic
The addition of predicate logic represents an additional layer of difficulty.
Keep [the additional axioms](tests/axioms_predicate.px) within reach as a reference.
Consider the following example proofs:

```
TODO
```

Contribute
----------
This project is licensed under the [GPLv3](./LICENSE).
Contributions welcome!

Future ideas:
 * semantics assistance?
 * modal logic (would fit well with axiom sets, but natural deduction sucks)
 * ...

