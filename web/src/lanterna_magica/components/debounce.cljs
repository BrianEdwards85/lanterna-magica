(ns lanterna-magica.components.debounce
  "Helpers for managing debounced functions in Reagent component lifecycles."
  (:require
   ["lodash.debounce" :as debounce]))

(defn make-debounced-fn
  "Returns an atom holding a debounced wrapper around `f` with `delay-ms`
   milliseconds of delay (default 500).

   Intended use: call this once at component construction time (the outer
   `let` of a form-2 or r/create-class component) and store the result.
   In :component-will-unmount, call `cancel-debounced-fn!` to flush/cancel
   any pending invocation.

   Example (form-2):

     (defn my-comp []
       (let [debounced (make-debounced-fn #(rf/dispatch [:my-event]) 300)]
         (fn []
           [:button {:on-click #(@debounced)} \"Go\"])))

   Example (r/create-class):

     (defn my-comp []
       (let [debounced (make-debounced-fn #(rf/dispatch [:my-event]))]
         (r/create-class
           {:component-will-unmount (fn [_] (cancel-debounced-fn! debounced))
            :reagent-render         (fn [] [:button {:on-click #(@debounced)} \"Go\"])})))"
  ([f]
   (make-debounced-fn f 500))
  ([f delay-ms]
   (atom (debounce f delay-ms))))

(defn cancel-debounced-fn!
  "Cancels any pending invocation of the debounced function stored in `debounced-atom`.
   Safe to call even when the atom holds nil."
  [debounced-atom]
  (when-let [d @debounced-atom]
    (.cancel d)))
