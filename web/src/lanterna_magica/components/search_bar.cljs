(ns lanterna-magica.components.search-bar
  "Search bar and archive toggle components."
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.components.inputs :as inputs]))

;; ---------------------------------------------------------------------------
;; Archive Toggle
;; ---------------------------------------------------------------------------

(defn archive-toggle
  [{:keys [checked on-change]}]
  [bp/switch-control {:checked   (boolean checked)
                      :label     "Archived"
                      :class     "mb-0"
                      :on-change (fn [_] (on-change))}])

;; ---------------------------------------------------------------------------
;; Search + Archive Bar
;; ---------------------------------------------------------------------------

(defn search-bar
  [{:keys [search on-search-change show-archived on-toggle-archived placeholder]}]
  [:div {:class "flex items-center gap-3 mb-4"}
   [:div.flex-1
    [inputs/search-input {:value       search
                          :on-change   on-search-change
                          :placeholder placeholder}]]
   [archive-toggle {:checked   show-archived
                    :on-change on-toggle-archived}]])
