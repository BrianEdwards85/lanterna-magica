(ns lanterna-magica.components.json-block
  "Renders a pretty-printed JSON value in a pre block.")

;; ---------------------------------------------------------------------------
;; JSON Block
;; ---------------------------------------------------------------------------

(defn json-block
  "Renders `v` as a formatted JSON block.
   Props: {:value <any clj value>
           :class  <optional extra CSS classes string>}"
  [{:keys [value class]}]
  [:pre {:class (str "json-display" (when class (str " " class)))}
   (.stringify js/JSON (clj->js value) nil 2)])
