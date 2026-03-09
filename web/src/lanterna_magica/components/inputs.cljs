(ns lanterna-magica.components.inputs
  "Local-state text input components."
  (:require
   ["lodash.debounce" :as debounce]
   [lanterna-magica.bp :as bp]
   [reagent.core :as r]))

;; ---------------------------------------------------------------------------
;; Local-state text input (prevents cursor-jump on re-frame round-trip)
;; ---------------------------------------------------------------------------

(defn local-input
  "A text input that uses local state to avoid cursor-jump issues.
   Props: :value, :on-change, :placeholder, :disabled, and any extra keys
   passed to the underlying <input>."
  [{:keys [value]}]
  (let [local (r/atom (or value ""))]
    (fn [{:keys [value on-change placeholder disabled] :as props}]
      (when (and (some? value) (not= value @local))
        (reset! local value))
      [:input.bp6-input.w-full
       (merge (dissoc props :on-change)
              {:value     @local
               :on-change #(let [v (.. % -target -value)]
                             (reset! local v)
                             (when on-change (on-change v)))})])))

(defn local-textarea
  "A textarea using Blueprint TextArea with local state to avoid cursor-jump issues.
   Props: :value, :on-change, :rows, :placeholder, :class, and any extra keys."
  [{:keys [value]}]
  (let [local (r/atom (or value ""))]
    (fn [{:keys [value on-change class] :as props}]
      (when (and (some? value) (not= value @local))
        (reset! local value))
      [bp/text-area
       (merge (dissoc props :on-change :class)
              {:fill      true
               :class-name class
               :value     @local
               :on-change #(let [v (.. % -target -value)]
                             (reset! local v)
                             (when on-change (on-change v)))})])))

;; ---------------------------------------------------------------------------
;; Search Input
;; ---------------------------------------------------------------------------

(defn search-input
  "Search input with local state and 500ms debounce on on-change."
  [{:keys [value]}]
  (let [local           (r/atom (or value ""))
        debounced-fn    (atom nil)]
    (r/create-class
      {:component-will-unmount
       (fn [_]
         (when-let [d @debounced-fn]
           (.cancel d)))

       :reagent-render
       (fn [{:keys [value on-change placeholder]}]
         (when (and (some? value) (not= value @local))
           (reset! local value))
         (when (nil? @debounced-fn)
           (reset! debounced-fn (debounce (fn [v] (on-change v)) 500)))
         [bp/input-group {:left-icon   "search"
                          :placeholder (or placeholder "Search...")
                          :value       (or @local "")
                          :on-change   #(let [v (.. % -target -value)]
                                          (reset! local v)
                                          (@debounced-fn v))}])})))
