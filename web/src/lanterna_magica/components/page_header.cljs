(ns lanterna-magica.components.page-header
  "Page header component with title and action buttons."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Page Header
;; ---------------------------------------------------------------------------

(defn page-header
  [{:keys [title loading? on-refresh on-create]}]
  [:div.flex.items-center.justify-between.mb-4
   [:h3.bp6-heading title]
   [:div.flex.items-center.gap-2
    (when on-create
      [bp/button {:icon     "plus"
                  :intent   "primary"
                  :minimal  true
                  :on-click on-create}])
    [bp/button {:icon     "refresh"
                :minimal  true
                :loading  loading?
                :on-click on-refresh}]]])
