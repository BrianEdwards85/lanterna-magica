(ns lanterna-magica.components.load-more
  "Load more pagination button component."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Pagination - Load More
;; ---------------------------------------------------------------------------

(defn load-more-button
  [{:keys [has-next? loading? on-click]}]
  (when has-next?
    [:div.text-center.mt-2
     [bp/button {:text     "Load more"
                 :minimal  true
                 :loading  loading?
                 :on-click on-click}]]))
