(ns lanterna-magica.components.states
  "Loading and empty state components."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Loading / Empty States
;; ---------------------------------------------------------------------------

(defn loading-spinner []
  [:div.py-8.text-center [bp/spinner {:size 40}]])

(defn empty-state
  [{:keys [icon title description]}]
  [bp/non-ideal-state {:icon        icon
                       :title       title
                       :description description}])
