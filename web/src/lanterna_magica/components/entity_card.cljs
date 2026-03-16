(ns lanterna-magica.components.entity-card
  "Entity card component for list items."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Entity Card
;; ---------------------------------------------------------------------------

(defn entity-card
  [{:keys [name description archived? on-click badges]}]
  [:div {:class    (str "mb-2 rounded p-3 cursor-pointer transition-all "
                        "bg-tn-bg-card hover:brightness-110"
                        (when archived? " opacity-60"))
         :on-click on-click}
   [:div.flex.items-center.justify-between
    [:div.flex.items-center.gap-2
     [:span {:class (str "font-semibold" (when archived? " line-through"))} name]
     (when archived?
       [bp/tag {:minimal true :class "ml-2"} "archived"])
     (when badges
       (into [:<>] badges))]
    [bp/icon {:icon "chevron-right" :class "opacity-50"}]]
   (when (seq description)
     [:p {:class "text-sm opacity-60 mt-1 mb-0"} description])])
