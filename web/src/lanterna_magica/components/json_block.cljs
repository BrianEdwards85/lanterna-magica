(ns lanterna-magica.components.json-block
  "Renders a pretty-printed JSON value in a read-only Monaco editor."
  (:require [clojure.string :as str]
            [lanterna-magica.components.monaco-editor :as monaco]))

;; ---------------------------------------------------------------------------
;; JSON Block
;; ---------------------------------------------------------------------------

(defn json-block
  "Renders `v` as a syntax-highlighted, foldable, read-only JSON block.
   Props: {:value <any clj value>
           :class  <optional extra CSS classes string>}"
  [{:keys [value class]}]
  (let [text (js/JSON.stringify (clj->js value) nil 2)
        line-count (count (str/split-lines text))
        height (str (min 400 (max 80 (* 19 line-count))) "px")]
    [:div {:class class}
     [monaco/monaco-editor
      {:value     text
       :language  "json"
       :read-only true
       :height    height}]]))
