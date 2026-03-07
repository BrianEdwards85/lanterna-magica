(ns lanterna-magica.routes
  (:require [lanterna-magica.events :as-alias events]
            [re-frame.core :as rf]
            [reitit.frontend :as rtf]
            [reitit.frontend.easy :as rtfe]))

(def routes
  [["/"                {:name :route/home}]
   ["/dimensions"      {:name :route/dimensions}]
   ["/dimension-types" {:name :route/dimension-types}]
   ["/shared-values"   {:name :route/shared-values}]
   ["/configurations"  {:name :route/configurations}]])

(defn on-navigate [match _history]
  (when match
    (rf/dispatch [::navigated match])))

(defn start! []
  (rtfe/start!
   (rtf/router routes)
   on-navigate
   {:use-fragment false}))

(def ^:private route->fetch-event
  {:route/dimensions      [::events/fetch-dimension-types]
   :route/dimension-types [::events/fetch-dimension-types]
   :route/shared-values   [::events/fetch-shared-values]
   :route/configurations  [::events/fetch-configurations]})

(rf/reg-event-fx
 ::navigated
 (fn [{:keys [db]} [_ match]]
   (let [route-name (get-in match [:data :name])
         effects    {:db (assoc db :current-route match)}]
     (if-let [event (route->fetch-event route-name)]
       (assoc effects :dispatch event)
       effects))))

(defn navigate! [route-name]
  (rtfe/navigate route-name))

(defn href [route-name]
  (rtfe/href route-name))
