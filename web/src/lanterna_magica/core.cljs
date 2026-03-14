(ns lanterna-magica.core
  (:require
   [lanterna-magica.events :as events]
   [lanterna-magica.routes :as routes]
   [lanterna-magica.subs :as subs]
   [lanterna-magica.views.configurations :as configurations]
   [lanterna-magica.views.dimensions :as dimensions]
   [lanterna-magica.views.header :as header]
   [lanterna-magica.views.home :as home]
   [lanterna-magica.views.shared-values :as shared-values]
   [re-frame.core :as rf]
   [reagent.dom.client :as rdc]))

(defonce root (atom nil))

(defn current-page []
  (let [route-name @(rf/subscribe [::subs/current-route-name])]
    (case route-name
      :route/home             [home/home-screen]
      :route/dimensions       [dimensions/dimensions-screen]
      :route/shared-values    [shared-values/shared-values-screen]
      :route/shared-value     [shared-values/shared-values-screen]
      :route/configurations   [configurations/configurations-screen]
      :route/configuration    [configurations/configurations-screen]
      [home/home-screen])))

(defn app []
  [:<>
   [header/header]
   [current-page]])

(defn ^:export init []
  (rf/dispatch-sync [::events/initialize-db])
  (rf/dispatch [::events/boot])
  (routes/start!)
  (let [container (js/document.getElementById "app")]
    (if-let [r @root]
      (rdc/render r [app])
      (let [r (rdc/create-root container)]
        (reset! root r)
        (rdc/render r [app])))))
