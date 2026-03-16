(ns lanterna-magica.components.dimensions-label
  "Renders a list of dimension maps as Blueprint tags."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Dimensions Label
;; ---------------------------------------------------------------------------

(defn dimensions-label
  "Render a list of dimensions as tags in the format 'type-name: dim-name'."
  [dimensions]
  [:div.flex.items-center.gap-1.flex-wrap
   (for [dim dimensions]
     ^{:key (:id dim)}
     [bp/tag {:minimal true}
      (str (get-in dim [:type :name]) ": " (:name dim))])])
