(ns lanterna-magica.subs
  (:require [re-frame.core :as rf]))

;; -- Route ----------------------------------------------------------------

(rf/reg-sub ::current-route      (fn [db _] (:current-route db)))

(rf/reg-sub ::current-route-name
 :<- [::current-route]
 (fn [route _] (-> route :data :name)))

;; -- Dimension Types ------------------------------------------------------

(rf/reg-sub ::dimension-types    (fn [db _] (:dimension-types db)))
(rf/reg-sub ::show-archived-types (fn [db _] (:show-archived-types db)))

;; -- Dimensions (per type) ------------------------------------------------

(rf/reg-sub ::selected-dimension-type-id
 (fn [db _] (:selected-dimension-type-id db)))

(rf/reg-sub ::dimensions-page
 (fn [db [_ type-id]]
   (get-in db [:dimensions-pages type-id]
           {:edges [] :page-info {:hasNextPage false :endCursor nil}
            :search "" :show-archived false})))

(rf/reg-sub ::all-dimensions
 (fn [db [_ type-id]]
   (get-in db [:all-dimensions type-id] [])))

(rf/reg-sub ::dimensions-search-results
 (fn [db [_ type-id]]
   (get-in db [:dimensions-search-results type-id])))

(rf/reg-sub ::dimensions-dropdown-items
 (fn [db [_ type-id]]
   (or (get-in db [:dimensions-search-results type-id])
       (get-in db [:all-dimensions type-id] []))))

;; -- Entity page state ----------------------------------------------------

(rf/reg-sub ::shared-values-page  (fn [db _] (:shared-values-page db)))
(rf/reg-sub ::configurations-page (fn [db _] (:configurations-page db)))

;; -- Dialog state ---------------------------------------------------------

(rf/reg-sub ::dimension-type-dialog (fn [db _] (:dimension-type-dialog db)))
(rf/reg-sub ::dimension-dialog      (fn [db _] (:dimension-dialog db)))
(rf/reg-sub ::shared-value-dialog   (fn [db _] (:shared-value-dialog db)))
(rf/reg-sub ::revision-dialog       (fn [db _] (:revision-dialog db)))
(rf/reg-sub ::configuration-dialog  (fn [db _] (:configuration-dialog db)))

;; -- Loading / Errors -----------------------------------------------------

(rf/reg-sub ::loading        (fn [db _] (:loading db)))

(rf/reg-sub ::loading?
 :<- [::loading]
 (fn [loading [_ key]] (contains? loading key)))

(rf/reg-sub ::errors         (fn [db _] (:errors db)))

(rf/reg-sub ::error
 :<- [::errors]
 (fn [errors [_ key]] (get errors key)))
